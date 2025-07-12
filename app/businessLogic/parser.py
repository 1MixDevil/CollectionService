import asyncio
import aiohttp
import re
import os
import logging
from aiohttp import ClientSession
from lxml import html
from typing import Optional, List, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.figures_model import CollectType, Figure

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s"
)
logger = logging.getLogger("FastFigureUpdater")

class FastFigureUpdater:
    BASE_URL = "https://www.bricklink.com/v2/catalog/catalogitem.page?M={item_id}"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    CONCURRENCY = 20
    FETCH_TIMEOUT = 10

    @staticmethod
    def get_last_id(db: Session, article: str) -> Tuple[int, str]:
        ct = db.query(CollectType).filter_by(article=article).first()
        if not ct:
            raise ValueError(f"CollectType '{article}' не найден.")
        last: Optional[Figure] = (
            db.query(Figure)
            .filter(Figure.type_collected_id == ct.id)
            .order_by(Figure.bricklink_id.desc())
            .first()
        )
        if not last:
            logger.info(f"[{article}] No last figure found, starting from 0")
            return 0, ''
        raw = last.bricklink_id[len(article):]
        m = re.match(r"(\d+)([a-z]?)", raw)
        if not m:
            logger.warning(f"[{article}] Unexpected bricklink_id format: {last.bricklink_id}")
            return 0, ''
        num, suffix = int(m.group(1)), m.group(2)
        logger.info(f"[{article}] Last known ID: {last.bricklink_id} → num={num}, suffix='{suffix}'")
        return num, suffix

    @staticmethod
    async def fetch_name(session: ClientSession, item_id: str) -> Optional[str]:
        url = FastFigureUpdater.BASE_URL.format(item_id=item_id)
        try:
            async with session.get(url, headers=FastFigureUpdater.HEADERS, timeout=FastFigureUpdater.FETCH_TIMEOUT) as resp:
                logger.info(f"Request: {item_id} → HTTP {resp.status}")
                if resp.status != 200:
                    return None
                text = await resp.text()
            tree = html.fromstring(text)
            desc = tree.xpath("//meta[@name='description']/@content")
            if not desc:
                return None
            m = re.search(r"ItemName:\s*(.*?),\s*ItemType:", desc[0])
            return m.group(1).strip() if m else None
        except Exception as e:
            logger.warning(f"Error fetching {item_id}: {e}")
            return None

    @staticmethod
    async def collect_figures(
        article: str,
        start_num: int,
        start_suffix: str,
        max_miss: int,
        max_suffix: int,
        pad_length: int = 4
    ) -> List[Tuple[str, str]]:

        logger.info(f"[{article}] Starting collection with pad_length={pad_length}")

        results = []
        seen_ids = set()

        miss = 0
        miss_suffix = 0
        num = start_num
        suffix = chr(ord(start_suffix) + 1) if start_suffix else ''
        
        timeout = aiohttp.ClientTimeout(total=FastFigureUpdater.FETCH_TIMEOUT)
        connector = aiohttp.TCPConnector(limit=FastFigureUpdater.CONCURRENCY)
        semaphore = asyncio.Semaphore(FastFigureUpdater.CONCURRENCY)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            while True:
                candidates = []
                suffixes = []

                if suffix:
                    for _ in range(max_suffix - miss_suffix):
                        item_id = f"{article}{num:0{pad_length}d}{suffix}"
                        candidates.append(item_id)
                        suffixes.append(suffix)
                        suffix = chr(ord(suffix) + 1)
                else:
                    item_id = f"{article}{num:0{pad_length}d}"
                    candidates.append(item_id)
                    suffixes.append('')

                async def fetch_and_record(item_id: str):
                    async with semaphore:
                        name = await FastFigureUpdater.fetch_name(session, item_id)
                        return item_id, name

                tasks = [fetch_and_record(cid) for cid in candidates]
                responses = await asyncio.gather(*tasks)

                any_found = False
                for item_id, name in responses:
                    seen_ids.add(item_id)
                    if name:
                        logger.info(f"FOUND     {item_id} → {name}")
                        results.append((item_id, name))
                        any_found = True
                    else:
                        logger.info(f"MISS      {item_id}")

                if suffixes[0] != '':
                    if any_found:
                        miss = 0
                        miss_suffix = 0
                        suffix = chr(ord(suffixes[-1]) + 1)
                    else:
                        miss_suffix += len(suffixes)
                        logger.info(f"MISS_SUFFIX COUNT = {miss_suffix} for num={num}")
                        if miss_suffix >= max_suffix:
                            logger.info(f"Switching to next number (no suffixes valid)")
                            miss_suffix = 0
                            suffix = ''
                            num += 1
                else:
                    if any_found:
                        miss = 0
                        num += 1
                    else:
                        miss += 1
                        logger.info(f"MISS_NUM COUNT = {miss} for num={num}")
                        if miss >= max_miss:
                            logger.info(f"Reached max_miss={max_miss}, stopping.")
                            break
                        num += 1

                await asyncio.sleep(0.1)

        logger.info(f"Total new records collected: {len(results)}")
        return results


    @staticmethod
    def insert_new_figures(db: Session, ct: CollectType, records: List[Tuple[str, str]]) -> int:
        if not records:
            logger.info("No new records to insert.")
            return 0

        ids = [rid for rid, _ in records]
        existing: Set[str] = {
            row[0] for row in db.query(Figure.bricklink_id).filter(Figure.bricklink_id.in_(ids))
        }
        logger.info(f"Filtered out {len(existing)} duplicates from {len(records)} records")
        new = [(rid, name) for rid, name in records if rid not in existing]

        objs = [
            Figure(bricklink_id=rid, name=name, type_collected_id=ct.id)
            for rid, name in new
        ]
        try:
            db.bulk_save_objects(objs)
            db.commit()
            logger.info(f"Inserted {len(objs)} new figures (bulk)")
            return len(objs)
        except IntegrityError:
            db.rollback()
            count = 0
            for obj in objs:
                try:
                    db.add(obj)
                    db.commit()
                    count += 1
                except IntegrityError:
                    db.rollback()
            logger.warning(f"Inserted {count} new figures (with fallback due to IntegrityError)")
            return count

    @staticmethod
    async def update(
        db: Session,
        article: str,
        max_miss: int = 50,
        max_suffix: int = 5,
        lock: bool = True,
        pad_length: int = 4
    ) -> int:
        if lock:
            lock_file = f"/tmp/bricklink_{article}.lock"
            if os.path.exists(lock_file):
                logger.warning(f"Скрипт уже запущен для {article}")
                return 0
            open(lock_file, 'w').close()

        try:
            last_num, last_suffix = FastFigureUpdater.get_last_id(db, article)
            new_records = await FastFigureUpdater.collect_figures(
                article=article,
                start_num=last_num,
                start_suffix=last_suffix,
                max_miss=max_miss,
                max_suffix=max_suffix,
                pad_length=pad_length
            )
            if not new_records:
                logger.info(f"No new records found for article={article}")
                return 0
            ct = db.query(CollectType).filter_by(article=article).first()
            if not ct:
                raise ValueError(f"CollectType с article={article} не найден")
            return FastFigureUpdater.insert_new_figures(db, ct, new_records)
        finally:
            if lock:
                os.remove(lock_file)
