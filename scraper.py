import argparse
import gzip
import os
import re
import shutil
import time
from concurrent.futures import ProcessPoolExecutor


class LogScraper:
    def __init__(self, input_dir: str, output_dir: str):
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Der Ordner {input_dir} existiert nicht.")

        self.input_dir = input_dir
        self.output_dir = self.get_unique_output_dir(output_dir)

        self.file_handles = {}

        self.threading = False
        self.process_time = 0.0

    @staticmethod
    def get_unique_output_dir(base_dir: str) -> str:
        counter = 1
        while os.path.exists(new_dir := f"{base_dir}_{counter}"):
            counter += 1
        return new_dir if os.path.exists(base_dir) else base_dir

    def process_directory(self) -> None:
        os.makedirs(self.output_dir)
        start_time = time.time()

        if self.threading:
            with ProcessPoolExecutor(max_workers=4) as executor:
                executor.map(self.process_archive, os.listdir(self.input_dir))

        else:
            for archive in os.listdir(self.input_dir):
                self.process_archive(archive)

        self.process_time = time.time() - start_time
        self.close_files()

    def process_archive(self, archive: str) -> None:
        if not archive.endswith(".gz"):
            return

        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", archive)
        if not date_match:
            return
        date = date_match.group(1)

        try:
            archive_path = os.path.join(self.input_dir, archive)
            with gzip.open(archive_path, "rt", errors="replace") as log_file:
                for line in log_file:
                    self.process_line(line, date)
            print(f"Finished {archive}")

        except Exception as err:
            print(f"Skipping {archive} - error: {err}")

    def process_line(self, line: str, date: str) -> None:
        if "[CityBuild]" not in line or "#" not in line:
            return

        time_placement_match = re.search(r"\[(.*?)].*?#(\d+)", line)
        if not time_placement_match:
            return

        date_time = f"{date} {time_placement_match.group(1)}"
        placement = int(time_placement_match.group(2))
        if not 1 <= placement <= 10:
            return

        info = line.split("#", 1)[1].split("[", 1)[0].strip()
        if len(info.split()) < 3:
            return

        self.write_to_file(date_time, info)

    def write_to_file(self, date_time: str, info: str) -> None:
        if "Besuche" in info or "visits" in info:
            output_file_name = "Warps"
        elif "$" in info:
            output_file_name = "Gilden"
        elif "Level" in info:
            output_file_name = "Level"
            info = info.replace("?", "★")  # Spürbare Laufzeiterhöhung Testen
        elif "Job-XP" in info or "Job XP" in info:
            output_file_name = "Job"
        elif "Mobs" in info or "mobs" in info:
            output_file_name = "Collection"
        elif "Plotlevel" in info or "Plot level" in info:
            output_file_name = "Plot level"
        else:
            output_file_name = "Rest"

        file_path = os.path.join(self.output_dir, f"{output_file_name}.txt")
        if file_path not in self.file_handles:
            self.file_handles[file_path] = open(file_path, "a", encoding="utf-8")

        self.file_handles[file_path].write(f"{date_time} {info}\n")

    def close_files(self) -> None:
        for file in self.file_handles.values():
            file.close()

    def pack_directory(self) -> None:
        shutil.make_archive(self.output_dir, 'zip', self.output_dir)
        print(f"Archiv {self.output_dir}.zip erstellt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrahiert CityBuild Toplist-Daten aus Minecraft-Logs und speichert sie in einem Ordner.")
    parser.add_argument("input_path", type=str, help="Pfad zum Log-Ordner")
    parser.add_argument("output_name", type=str, help="Name des Zielordners für die extrahierten Daten")

    parser.add_argument("--pack", action="store_true", help="Komprimiert den Ausgabeordner als ZIP-Datei")
    parser.add_argument("--threading", action="store_true", help="Aktiviere Multithreading")

    args = parser.parse_args()

    try:
        scraper = LogScraper(args.input_path, args.output_name)
    except FileNotFoundError as e:
        print(e)
    else:
        if args.threading:
            scraper.threading = True

        scraper.process_directory()
        print(f"\nFertig nach {scraper.process_time:.2f}s.")

        if args.pack:
            scraper.pack_directory()
