import argparse
import gzip
import os
import re
import shutil
import time
from concurrent.futures import ProcessPoolExecutor

from enum import Enum


class OutputType(Enum):
    Warp = "Warp Top"
    Guild = "Guild Top"
    Level = "Level Top"
    Job = "Job Top"
    Collection = "Collection Top"
    PlotLevel = "PlotLevel Top"

    CrateOpened = "Crates Opened"
    CrateDrop = "Crates Drops"

    Talisman = "Talisman"

    Unsorted = "Unsorted"


class TalismanRarity(Enum):
    Legendary = 24
    Epic = 18
    Rare = 12
    Common = 6


class FileHandler:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.file_handles = {}

    def write(self, file: OutputType, content: str) -> None:
        file_path = os.path.join(self.output_dir, f"{file.value}.txt")
        if file_path not in self.file_handles:
            self.file_handles[file_path] = open(file_path, "a", encoding="utf-8")

        self.file_handles[file_path].write(content + "\n")

    def close(self) -> None:
        for file in self.file_handles.values():
            file.close()


class LogScraper:
    def __init__(self, input_dir: str, output_dir: str):
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"Der Ordner {input_dir} existiert nicht.")

        self.input_dir = input_dir
        self.output_dir = self.get_unique_output_dir(output_dir)
        self.file_handler = FileHandler(self.output_dir)

        self.search_toplist = False
        self.search_crates = False
        self.search_talisman = False

        self.time_pattern = re.compile(r"\[(\d{2}:\d{2}:\d{2})]")

        self.toplist_pattern = re.compile(r"\[(\d{2}:\d{2}:\d{2})].*?#(\d+)\s+([^\[]+)")
        self.crate_open_pattern = re.compile(
            r"\b(?:ffnest eine crate vom typ|you are opening a crate of the type) ([^\[]+)\b",
            re.IGNORECASE
        )
        self.crate_drop_pattern = re.compile(
            r"\b(?:du hast (.+?) erhalten|you have received (.+))\b",
            re.IGNORECASE
        )
        self.talisman_pattern = re.compile(
            r"(?:herstellung eines talismans begonnen|started the manufacturing of a talisman).*?(\d+(?:[.,]\d+)?)\s*(?:stunden|hours)",
            re.IGNORECASE
        )

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
            with ProcessPoolExecutor() as executor:
                executor.map(self.process_archive, os.listdir(self.input_dir))

        else:
            for archive in os.listdir(self.input_dir):
                self.process_archive(archive)

        self.process_time = time.time() - start_time
        self.file_handler.close()

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
        if "[CityBuild]" not in line:
            return

        time_match = self.time_pattern.search(line)
        if not time_match:
            return
        date_time = f"{date} {time_match.group(1)}"

        if self.search_toplist and "#" in line:
            if self.__handle_toplist(line, date_time):
                return

        if self.search_crates:
            if self.__handle_crate(line, date_time):
                return

        if self.search_talisman:
            if self.__handle_talisman(line, date_time):
                return

    def __handle_toplist(self, line: str, date_time: str) -> bool:
        match = self.toplist_pattern.search(line)
        if not match:
            return False

        placement = int(match.group(2))
        if not (1 <= placement <= 10):
            return False

        info = match.group(3).strip()
        if len(info) < 3:
            return False

        category = OutputType.Unsorted
        if "Besuche" in info or "visits" in info:
            category = OutputType.Warp
        elif "$" in info:
            category = OutputType.Guild
        elif "Level" in info:
            info = info.replace("?", "★")
            category = OutputType.Level
        elif "Job-XP" in info or "Job XP" in info:
            category = OutputType.Job
        elif "Mobs" in info or "mobs" in info:
            category = OutputType.Collection
        elif "Plotlevel" in info or "Plot level" in info:
            info = info.replace("Plot level", "Plotlevel")
            category = OutputType.PlotLevel

        self.file_handler.write(category, f"{date_time} {placement} {info}")
        return True

    def __handle_crate(self, line: str, date_time: str) -> bool:
        open_match = self.crate_open_pattern.search(line)
        if open_match:
            crate_type = open_match.group(1)
            self.file_handler.write(OutputType.CrateOpened, f"{date_time} {crate_type}")
            return True

        drop_match = self.crate_drop_pattern.search(line)
        if drop_match:
            reward = drop_match.group(1) or drop_match.group(2)
            if "$" or "Item" in reward:
                return False
            self.file_handler.write(OutputType.CrateDrop, f"{date_time} {reward}")
            return True

        return False

    def __handle_talisman(self, line: str, date_time: str) -> bool:
        match = self.talisman_pattern.search(line)
        if match:
            hours = int(match.group(1))
            self.file_handler.write(OutputType.Talisman, f"{date_time} {TalismanRarity(hours).name}")
            return True

        return False

    def pack_directory(self) -> None:
        shutil.make_archive(self.output_dir, 'zip', self.output_dir)
        print(f"Archiv {self.output_dir}.zip erstellt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrahiert CityBuild Toplist-Daten aus Minecraft-Logs und speichert sie in einem Ordner.")
    parser.add_argument("input_path", type=str, help="Pfad zum Log-Ordner")
    parser.add_argument("output_name", type=str, help="Name des Zielordners für die extrahierten Daten")

    parser.add_argument("--toplist", action="store_true", help="Suche nach aufgerufenen Toplisten")
    parser.add_argument("--crates", action="store_true", help="Suche nach geöffneten Crates")
    parser.add_argument("--talisman", action="store_true", help="Suche hergestellten Talismanen")

    parser.add_argument("--threading", action="store_true", help="Aktiviere Multithreading")
    parser.add_argument("--pack", action="store_true", help="Komprimiert den Ausgabeordner als ZIP-Datei")

    args = parser.parse_args()

    try:
        scraper = LogScraper(args.input_path, args.output_name)
    except FileNotFoundError as e:
        print(e)
    else:
        if args.toplist:
            scraper.search_toplist = True
        if args.crates:
            scraper.search_crates = True
        if args.talisman:
            scraper.search_talisman = True

        if args.threading:
            scraper.threading = True

        if scraper.search_toplist or scraper.search_crates or scraper.search_talisman:
            scraper.process_directory()
            print(f"\nFertig nach {scraper.process_time:.2f}s.")

            if args.pack:
                scraper.pack_directory()

        else:
            print("Kein Argument angegeben.")
