# Stuttgart Streets

A comprehensive Python project to collect all street names and house numbers in Stuttgart using the city's autocomplete APIs.

## Overview

This project systematically collects complete address data for Stuttgart by using two autocomplete services:
1. **Street Names**: Collects all street names in the city
2. **House Numbers**: For each street, collects all valid house numbers

Both APIs return up to 12 suggestions per query, requiring recursive exploration for complete coverage.

## API Details

### Street Names API
- **Endpoint**: `https://service.stuttgart.de/lhs-services/aws/strassennamen?street={prefix}`
- **Response**: JSON with up to 12 street suggestions
- **Fields**: Each suggestion contains `value` and `data` (which appear to be identical)

### House Numbers API
- **Endpoint**: `https://service.stuttgart.de/lhs-services/aws/hausnummern?street={street}&streetnr={number_prefix}`
- **Response**: JSON with up to 12 house number suggestions
- **Fields**: Each suggestion contains `value` and `data` for the house number
- **Note**: Empty `streetnr` parameter returns no results; must start with digit prefixes (1-9)

## Strategy

### Street Name Collection
Since the API returns a maximum of 12 results, we use a recursive approach:

1. Start with single letters (A, B, C, ..., Z, Ä, Ö, Ü)
2. If a prefix returns exactly 12 results, it likely has more streets
3. Extend the prefix with additional characters (Aa, Ab, Ac, ...)
4. Continue until the result count is less than 12
5. Store all unique street names found

### House Number Collection
For each street, we collect all valid house numbers:

1. Start with digit prefixes (1, 2, 3, ..., 9)
2. If a prefix returns exactly 12 results, extend with additional digits (10, 11, 12, ...)
3. Continue recursively until complete coverage
4. Handle complex German house number formats (A/B suffixes, slashes, etc.)

## German Address Format Support

### Street Name Phonetics
The script follows German phonetic rules when generating prefixes:
- Skips impossible combinations like "Kb", "Kc", "Kd", etc.
- Uses valid German letter combinations and umlauts (ä, ö, ü, ß)

### House Number Formats
Supports all Stuttgart house number formats:
- **Simple numbers**: 1, 2, 3, 10, 15, 100
- **Letter suffixes**: 30A, 30B, 55C
- **Slash numbers**: 30/1, 30/3, 9/1
- **Complex notations**: 68SE3, 85A,B,C,Du.87, 9Stockwerkseigentum

## Output Files

- `street_names.json`: All collected street names (3,654 streets)
- `completed_queries.json`: Street name prefixes that returned <12 results
- `street_numbers.json`: House numbers by street `{street_name: [numbers]}`

## Features

- **Resume Capability**: Loads existing data and continues where it left off
- **Progress Saving**: Auto-saves every 50 streets during house number collection
- **Error Handling**: Robust error handling with retry logic
- **Natural Sorting**: House numbers are sorted naturally (1, 2, 10, 11 vs 1, 10, 11, 2)

## Usage

```bash
# Install dependencies
uv add httpx

# Run the complete collection
uv run main.py
```

The script will:
1. Load any existing street name data
2. If needed, collect all street names (A-Z, Ä-Ö-Ü)
3. For each street, collect all valid house numbers
4. Save progress periodically and show real-time statistics

## Results

- **3,654 unique street names** in Stuttgart
- **Complete house number coverage** for all streets
- **Comprehensive address database** ready for geocoding, validation, or analysis

## Technical Implementation

- **Asynchronous HTTP requests** for performance
- **German phoneme-aware recursion** for street names
- **Digit-based recursion** for house numbers
- **JSON persistence** with UTF-8 encoding
- **Duplicate detection** and natural sorting