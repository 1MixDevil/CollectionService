import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO


class StarWarsCollageGenerator:
    @staticmethod
    def filter_by_keyword(
        data: list,
        name_key: str,
        keyword: str
    ) -> pd.DataFrame:
        """
        Filter list of dicts where name_key contains all words from keyword (case-insensitive).
        Returns a pandas DataFrame of matching records.
        """
        df = pd.DataFrame(data)
        words = keyword.lower().split()

        def contains_all(text: str) -> bool:
            text = str(text).lower()
            return all(w in text for w in words)

        return df[df[name_key].apply(contains_all)]

    @staticmethod
    def fetch_and_prepare_images(
        records: pd.DataFrame,
        id_key: str,
        prefix_url: str,
        min_height: int,
        font_path: str = 'arial.ttf',
        font_size: int = 90,
        user_agent: str = 'Mozilla/5.0'
    ) -> list:
        """
        Download images from BrickLink, resize, add padding and ID text.
        Returns list of PIL Image objects.
        """
        headers = {'User-Agent': user_agent}
        images = []

        try:
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            font = ImageFont.load_default()

        for _, row in records.iterrows():
            id_val = str(row[id_key])
            id_num = ''.join(filter(str.isdigit, id_val)) or id_val
            image_url = f"{prefix_url}{id_num}.png"

            resp = requests.get(image_url, headers=headers)
            if resp.status_code != 200:
                print(f"Skipping ID {id_val}: HTTP {resp.status_code}")
                continue

            img = Image.open(BytesIO(resp.content))
            ratio = img.width / img.height
            new_h = min_height
            new_w = int(new_h * ratio)
            img = img.resize((new_w, new_h))

            pad_top, pad_bottom = 150, 150
            canvas = Image.new('RGB', (new_w, new_h + pad_top + pad_bottom), (255, 255, 255))
            canvas.paste(img, (0, pad_top))

            draw = ImageDraw.Draw(canvas)
            draw.text((10, 10), id_val, font=font, fill=(0, 0, 0))
            images.append(canvas)

        return images

    @staticmethod
    def create_collage(
        images: list,
        output_path: str,
        columns: int = 5,
        max_images: int = None
    ) -> None:
        """
        Assemble and save a collage from a list of images.
        If max_images is set, only the first max_images will be used.
        """
        if not images:
            print("No images to create a collage.")
            return

        if max_images is not None and len(images) > max_images:
            print(f"Limiting images from {len(images)} to {max_images}.")
            images = images[:max_images]

        count = len(images)
        rows = (count + columns - 1) // columns
        w = max(img.width for img in images)
        h = max(img.height for img in images)

        collage = Image.new('RGB', (w * columns, h * rows), (255, 255, 255))
        for idx, img in enumerate(images):
            x = (idx % columns) * w
            y = (idx // columns) * h
            collage.paste(img, (x, y))

        collage.save(output_path)
        print(f"Collage saved to {output_path}")

    @staticmethod
    def generate_from_list(
        data: list,
        keyword: str,
        name_key: str,
        id_key: str,
        prefix_url: str,
        output_path: str,
        min_height: int = 1050,
        font_path: str = 'arial.ttf',
        font_size: int = 90,
        columns: int = 5,
        max_images: int = None
    ) -> None:
        """
        Full pipeline: filter list of dicts, download images, and build collage.
        """
        print(f"Filtering {len(data)} records by keyword '{keyword}'...")
        filtered_df = StarWarsCollageGenerator.filter_by_keyword(data, name_key, keyword)
        print(f"Found {len(filtered_df)} matching records.")

        print("Downloading and preparing images...")
        images = StarWarsCollageGenerator.fetch_and_prepare_images(
            filtered_df, id_key, prefix_url, min_height, font_path, font_size
        )
        print(f"Prepared {len(images)} images.")

        print("Assembling collage...")
        StarWarsCollageGenerator.create_collage(images, output_path, columns, max_images)


if __name__ == '__main__':
    sample_data = [
        {"name": "Luke Skywalker", "bricklink_id": "sw001"},
        {"name": "Darth Vader", "bricklink_id": "sw002"}
    ]
    StarWarsCollageGenerator.generate_from_list(
        data=sample_data,
        keyword='Skywalker',
        name_key='name',
        id_key='bricklink_id',
        prefix_url='https://img.bricklink.com/ItemImage/MN/0/sw',
        output_path='collage.png',
        min_height=1050,
        font_path='arial.ttf',
        font_size=90,
        columns=5,
        max_images=25
    )
