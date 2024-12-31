import unittest
from datetime import datetime
from models import Game


class TestVersionParsing(unittest.TestCase):
    def setUp(self):
        self.game = Game(game_id=1, name="Test Game", url="http://test.com")

    def test_version_extraction(self):
        test_cases = [
            # Semantic versions
            {
                "input": {
                    "filename": "game-v1.2.3.zip",
                    "display_name": "Game v1.2.3",
                    "build": {"user_version": None},
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "expected": "1.2.3"
            },
            # Version with single digit
            {
                "input": {
                    "filename": "game-13.zip",
                    "display_name": "Version 13",
                    "build": {"user_version": None},
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "expected": "13"
            },
            # Version with build number
            {
                "input": {
                    "filename": "Build_13_December2024-pc.zip",
                    "display_name": "Version 13",
                    "build": {"user_version": None},
                    "updated_at": "2024-12-31T07:37:49Z"
                },
                "expected": "13"
            },
            {
                "input": {
                    "filename": "Build_December2024_13-pc.zip",
                    "display_name": "Version 2024",
                    "build": {"user_version": None},
                    "updated_at": "2024-12-31T07:37:49Z"
                },
                "expected": "13"
            },
            # Version with letter suffix
            {
                "input": {
                    "filename": "game-1.0a.zip",
                    "display_name": "Game 1.0a",
                    "build": {"user_version": None},
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "expected": "1.0a"
            },
            # Version with 'v' prefix
            {
                "input": {
                    "filename": "game-v2.0.zip",
                    "display_name": "v2.0",
                    "build": {"user_version": None},
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "expected": "2.0"
            },
            # Build with user_version
            {
                "input": {
                    "filename": "game.zip",
                    "display_name": "Game",
                    "build": {"user_version": "3.1.4"},
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "expected": "3.1.4"
            },
            # Multiple version numbers - should pick semantic version
            {
                "input": {
                    "filename": "game-2024.1.2-v1.3.5.zip",
                    "display_name": "Game v1.3.5",
                    "build": {"user_version": None},
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "expected": "1.3.5"
            },
            # Date-like version that should be ignored
            {
                "input": {
                    "filename": "game-2024.12.31.zip",
                    "display_name": "Game v5.0",
                    "build": {"user_version": None},
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "expected": "5.0"
            },
            # No version - should fall back to date
            {
                "input": {
                    "filename": "game.zip",
                    "display_name": "Game",
                    "build": {"user_version": None},
                    "updated_at": "2024-12-31T00:00:00Z"
                },
                "expected": "2024.12.31"
            },
            # Single letter version
            {
                "input": {
                    "filename": "game-a.zip",
                    "display_name": "Game A",
                    "build": {"user_version": None},
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "expected": "2024.01.01"  # Should fall back to date
            },
            # Version with high numbers that look like years
            {
                "input": {
                    "filename": "game-2024.zip",
                    "display_name": "Version 13",
                    "build": {"user_version": None},
                    "updated_at": "2024-01-01T00:00:00Z"
                },
                "expected": "13"
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            upload = {
                "id": i,
                "filename": test_case["input"]["filename"],
                "display_name": test_case["input"]["display_name"],
                "build": test_case["input"]["build"],
                "updated_at": test_case["input"]["updated_at"]
            }
            result = self.game.extract_version(upload)
            self.assertEqual(
                result,
                test_case["expected"],
                f"Failed test case {i}:\nInput: {test_case['input']}\nExpected: {test_case['expected']}\nGot: {result}"
            )


if __name__ == '__main__':
    unittest.main()