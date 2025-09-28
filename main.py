import json
import httpx
from typing import List, Set, Dict
import asyncio
import os


class StuttgartStreetFetcher:
    def __init__(self):
        self.street_url = "https://service.stuttgart.de/lhs-services/aws/strassennamen"
        self.number_url = "https://service.stuttgart.de/lhs-services/aws/hausnummern"
        self.street_names: Set[str] = set()
        self.completed_queries: Set[str] = set()
        self.street_numbers: Dict[str, List[str]] = {}
        self.completed_number_queries: Set[str] = set()
        self.client = httpx.AsyncClient()

    async def fetch_streets(self, prefix: str) -> List[str]:
        """Fetch street suggestions for a given prefix."""
        try:
            response = await self.client.get(self.street_url, params={"street": prefix})
            response.raise_for_status()
            data = response.json()

            # Extract street names from the response
            street_names = []
            if isinstance(data, dict) and "suggestions" in data:
                for item in data["suggestions"]:
                    if isinstance(item, dict) and "data" in item:
                        street_names.append(item["data"])

            return street_names
        except Exception as e:
            print(f"Error fetching streets for prefix '{prefix}': {e}")
            return []

    async def fetch_house_numbers(self, street: str, number_prefix: str = "") -> List[str]:
        """Fetch house number suggestions for a given street and number prefix."""
        try:
            params = {"street": street}
            if number_prefix:
                params["streetnr"] = number_prefix

            response = await self.client.get(self.number_url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract house numbers from the response
            house_numbers = []
            if isinstance(data, dict) and "suggestions" in data:
                for item in data["suggestions"]:
                    if isinstance(item, dict) and "data" in item:
                        house_numbers.append(item["data"])

            return house_numbers
        except Exception as e:
            print(f"Error fetching house numbers for street '{street}' prefix '{number_prefix}': {e}")
            return []

    def get_next_characters(self, prefix: str) -> List[str]:
        """Generate next valid German characters for a prefix."""
        # German alphabet including umlauts
        german_chars = "abcdefghijklmnopqrstuvwxyzäöüß"

        # Skip impossible German letter combinations
        if len(prefix) >= 1:
            last_char = prefix[-1].lower()

            # Consonant clusters that are impossible in German
            impossible_after = {
                'b': ['b', 'c', 'd', 'f', 'g', 'j', 'k', 'p', 'q', 'v', 'w', 'x', 'z'],
                'c': ['b', 'c', 'd', 'f', 'g', 'j', 'p', 'q', 'v', 'w', 'x', 'y', 'z'],
                'd': ['b', 'c', 'd', 'f', 'g', 'j', 'k', 'p', 'q', 'v', 'w', 'x', 'z'],
                'f': ['b', 'c', 'd', 'g', 'j', 'k', 'p', 'q', 'v', 'w', 'x', 'z'],
                'g': ['b', 'c', 'd', 'f', 'j', 'k', 'p', 'q', 'v', 'w', 'x', 'z'],
                'k': ['b', 'c', 'd', 'f', 'g', 'j', 'k', 'p', 'q', 'v', 'w', 'x', 'z'],
                'p': ['b', 'c', 'd', 'g', 'j', 'k', 'p', 'q', 'v', 'w', 'x', 'z'],
                't': ['b', 'c', 'd', 'f', 'g', 'j', 'k', 'p', 'q', 'v', 'w', 'x'],
                'x': list("abcdefghijklmnopqrstuvwxyzäöüß"),  # x is very rare in German
                'q': [c for c in german_chars if c != 'u'],  # q almost always followed by u
            }

            if last_char in impossible_after:
                valid_chars = [c for c in german_chars if c not in impossible_after[last_char]]
                return valid_chars

        return list(german_chars)

    async def explore_house_numbers(self, street: str, number_prefix: str = ""):
        """Recursively explore all house numbers for a given street and number prefix."""
        query_key = f"{street}#{number_prefix}"

        if query_key in self.completed_number_queries:
            return

        print(f"Exploring house numbers for '{street}' with prefix '{number_prefix}'")

        house_numbers = await self.fetch_house_numbers(street, number_prefix)

        # Add all found house numbers to our collection
        if street not in self.street_numbers:
            self.street_numbers[street] = []

        for number in house_numbers:
            if number not in self.street_numbers[street]:
                self.street_numbers[street].append(number)

        # If we got exactly 12 results, there might be more
        if len(house_numbers) == 12:
            # Generate next digit prefixes (0-9)
            for digit in "0123456789":
                new_prefix = number_prefix + digit
                await self.explore_house_numbers(street, new_prefix)
        else:
            # This prefix is complete (less than 12 results)
            self.completed_number_queries.add(query_key)

    async def collect_house_numbers_for_street(self, street: str):
        """Collect all house numbers for a specific street."""
        # Check if this street is already fully processed
        if street in self.street_numbers:
            print(f"Street '{street}' already processed, skipping...")
            return

        # Start exploration with digit prefixes (1-9) since empty prefix returns nothing
        for digit in "123456789":
            await self.explore_house_numbers(street, digit)

    async def explore_prefix(self, prefix: str):
        """Recursively explore all streets with a given prefix."""
        print(f"Exploring prefix: {prefix}")

        streets = await self.fetch_streets(prefix)

        # Add all found streets to our collection
        for street in streets:
            self.street_names.add(street)

        # If we got exactly 12 results, there might be more
        if len(streets) == 12:
            # Generate next characters and explore deeper
            next_chars = self.get_next_characters(prefix)

            for char in next_chars:
                new_prefix = prefix + char
                await self.explore_prefix(new_prefix)
        else:
            # This prefix is complete (less than 12 results)
            self.completed_queries.add(prefix)

    async def collect_streets_starting_with(self, letter: str):
        """Collect all streets starting with a specific letter."""
        await self.explore_prefix(letter)

    def load_existing_data(self):
        """Load existing data from JSON files if they exist."""
        # Load street names
        if os.path.exists("street_names.json"):
            with open("street_names.json", "r", encoding="utf-8") as f:
                street_list = json.load(f)
                self.street_names = set(street_list)
                print(f"Loaded {len(self.street_names)} existing street names")

        # Load completed queries
        if os.path.exists("completed_queries.json"):
            with open("completed_queries.json", "r", encoding="utf-8") as f:
                query_list = json.load(f)
                self.completed_queries = set(query_list)
                print(f"Loaded {len(self.completed_queries)} existing completed queries")

        # Load street numbers
        if os.path.exists("street_numbers.json"):
            with open("street_numbers.json", "r", encoding="utf-8") as f:
                self.street_numbers = json.load(f)
                print(f"Loaded house numbers for {len(self.street_numbers)} streets")

    def save_results(self):
        """Save street names, completed queries, and house numbers to JSON files."""
        # Save street names
        with open("street_names.json", "w", encoding="utf-8") as f:
            json.dump(sorted(list(self.street_names)), f, ensure_ascii=False, indent=2)

        # Save completed queries
        with open("completed_queries.json", "w", encoding="utf-8") as f:
            json.dump(sorted(list(self.completed_queries)), f, ensure_ascii=False, indent=2)

        # Save street numbers (sort numbers within each street)
        sorted_street_numbers = {}
        for street, numbers in self.street_numbers.items():
            # Sort numbers naturally (handle both numeric and alphanumeric)
            try:
                sorted_numbers = sorted(numbers, key=lambda x: (int(''.join(filter(str.isdigit, x)) or '0'), x))
            except:
                sorted_numbers = sorted(numbers)
            sorted_street_numbers[street] = sorted_numbers

        with open("street_numbers.json", "w", encoding="utf-8") as f:
            json.dump(sorted_street_numbers, f, ensure_ascii=False, indent=2)

        print(f"Found {len(self.street_names)} unique street names")
        print(f"Completed {len(self.completed_queries)} street query branches")
        print(f"Found house numbers for {len(self.street_numbers)} streets")
        total_house_numbers = sum(len(numbers) for numbers in self.street_numbers.values())
        print(f"Total house numbers collected: {total_house_numbers}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


async def main():
    fetcher = StuttgartStreetFetcher()

    try:
        # Load existing data to resume where we left off
        fetcher.load_existing_data()

        # If we don't have street names yet, collect them first
        if not fetcher.street_names:
            print("=== COLLECTING STREET NAMES ===")
            # Collect streets for all letters A-Z and German umlauts
            letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ"

            for letter in letters:
                print(f"\n=== Starting collection for letter: {letter} ===")
                await fetcher.collect_streets_starting_with(letter)
                print(f"Current total: {len(fetcher.street_names)} streets, {len(fetcher.completed_queries)} completed queries")

            fetcher.save_results()
            print(f"\n=== STREET COLLECTION COMPLETE ===")
            print(f"Total unique streets found: {len(fetcher.street_names)}")

        # Now collect house numbers for all streets
        print(f"\n=== COLLECTING HOUSE NUMBERS ===")
        print(f"Processing {len(fetcher.street_names)} streets...")

        street_list = sorted(list(fetcher.street_names))
        for i, street in enumerate(street_list, 1):
            print(f"\n[{i}/{len(street_list)}] Processing street: {street}")
            await fetcher.collect_house_numbers_for_street(street)

            # Save progress every 50 streets
            if i % 50 == 0:
                fetcher.save_results()
                print(f"Progress saved - processed {i}/{len(street_list)} streets")

        fetcher.save_results()
        print(f"\n=== FINAL RESULTS ===")
        print(f"Total unique streets: {len(fetcher.street_names)}")
        print(f"Streets with house numbers: {len(fetcher.street_numbers)}")
        total_house_numbers = sum(len(numbers) for numbers in fetcher.street_numbers.values())
        print(f"Total house numbers collected: {total_house_numbers}")
    finally:
        await fetcher.close()


if __name__ == "__main__":
    asyncio.run(main())
