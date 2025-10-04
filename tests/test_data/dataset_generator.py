"""
Test Dataset Generator - Creates comprehensive test datasets for AI accuracy validation.

This module generates realistic test datasets with known ground truth labels
for validating AI analysis accuracy, confidence scoring, and safety layer integration.
"""

import json
import random
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass, asdict
import os

from src.ai_disk_cleanup.openai_client import FileMetadata
from src.ai_disk_cleanup.safety_layer import ProtectionLevel
from src.ai_disk_cleanup.core.ai_analyzer import PredictionType, ConfidenceScore


@dataclass
class TestCase:
    """Single test case with file metadata and expected results."""
    file_metadata: FileMetadata
    expected_recommendation: str  # delete, keep, manual_review
    expected_category: str
    expected_risk_level: str
    expected_confidence_range: Tuple[float, float]  # (min, max)
    protection_level: ProtectionLevel
    test_scenario: str
    difficulty_level: str  # easy, medium, hard
    ground_truth_reasoning: str


class DatasetGenerator:
    """
    Generates comprehensive test datasets for AI accuracy validation.

    Creates realistic file scenarios covering various edge cases, common patterns,
    and challenging situations to thoroughly test AI analysis capabilities.
    """

    def __init__(self, output_dir: str = "/home/malu/.projects/ai-disk-cleanup/tests/test_data"):
        """Initialize dataset generator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Test scenario weights
        self.scenario_weights = {
            'temporary_files': 0.25,
            'cache_files': 0.20,
            'log_files': 0.15,
            'backup_files': 0.10,
            'system_files': 0.10,
            'user_documents': 0.10,
            'edge_cases': 0.10
        }

        # File extensions by category
        self.extension_categories = {
            'temporary': ['.tmp', '.temp', '.tempfile', '.temp~', '.swp', '.swo'],
            'cache': ['.cache', '.cch', '.dat', '.db', '.sqlite', '.sqlite3'],
            'log': ['.log', '.out', '.err', '.trace', '.debug'],
            'backup': ['.bak', '.old', '.backup', '.orig', '.save', '.prev'],
            'document': ['.doc', '.docx', '.pdf', '.txt', '.rtf', '.odt'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv'],
            'archive': ['.zip', '.tar', '.gz', '.rar', '.7z', '.bz2'],
            'code': ['.py', '.js', '.html', '.css', '.cpp', '.java'],
            'system': ['.dll', '.exe', '.sys', '.drv', '.so', '.dylib'],
            'config': ['.conf', '.config', '.ini', '.cfg', '.yaml', '.yml', '.json']
        }

        # Risk level definitions
        self.risk_definitions = {
            'low': ['temporary', 'cache', 'log'],
            'medium': ['backup', 'config'],
            'high': ['document', 'image', 'video', 'archive'],
            'critical': ['system']
        }

        # Common file patterns
        self.file_patterns = {
            'temp_pattern': r'^.*\.tmp$|^.*\.temp$|^tmp.*$|^temp.*$',
            'backup_pattern': r'^.*\.bak$|^.*\.old$|^.*\.backup$|^.*~$',
            'cache_pattern': r'^.*cache.*$|^.*Cache.*$',
            'log_pattern': r'^.*\.log$|^.*log.*$',
            'date_pattern': r'^.*\d{4}-\d{2}-\d{2}.*$|^.*\d{8}.*$',
            'numbered_pattern': r'^.*\.\d+$|^.*\(\d+\).*$'
        }

    def generate_comprehensive_dataset(
        self,
        num_samples: int = 1000,
        dataset_name: str = "comprehensive_validation",
        difficulty_distribution: Dict[str, float] = None
    ) -> List[TestCase]:
        """
        Generate a comprehensive validation dataset.

        Args:
            num_samples: Number of test cases to generate
            dataset_name: Name for the dataset
            difficulty_distribution: Distribution of difficulty levels

        Returns:
            List of test cases
        """
        if difficulty_distribution is None:
            difficulty_distribution = {
                'easy': 0.4,
                'medium': 0.4,
                'hard': 0.2
            }

        test_cases = []

        # Generate samples for each scenario
        for scenario, weight in self.scenario_weights.items():
            scenario_count = int(num_samples * weight)
            scenario_cases = self._generate_scenario_test_cases(
                scenario, scenario_count, difficulty_distribution
            )
            test_cases.extend(scenario_cases)

        # Shuffle and ensure exact count
        random.shuffle(test_cases)
        test_cases = test_cases[:num_samples]

        # Save dataset
        self._save_dataset(test_cases, dataset_name)

        return test_cases

    def _generate_scenario_test_cases(
        self,
        scenario: str,
        count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[TestCase]:
        """Generate test cases for a specific scenario."""
        if scenario == 'temporary_files':
            return self._generate_temporary_file_cases(count, difficulty_distribution)
        elif scenario == 'cache_files':
            return self._generate_cache_file_cases(count, difficulty_distribution)
        elif scenario == 'log_files':
            return self._generate_log_file_cases(count, difficulty_distribution)
        elif scenario == 'backup_files':
            return self._generate_backup_file_cases(count, difficulty_distribution)
        elif scenario == 'system_files':
            return self._generate_system_file_cases(count, difficulty_distribution)
        elif scenario == 'user_documents':
            return self._generate_user_document_cases(count, difficulty_distribution)
        elif scenario == 'edge_cases':
            return self._generate_edge_case_tests(count, difficulty_distribution)
        else:
            raise ValueError(f"Unknown scenario: {scenario}")

    def _generate_temporary_file_cases(
        self,
        count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[TestCase]:
        """Generate temporary file test cases."""
        cases = []

        for i in range(count):
            difficulty = self._sample_difficulty(difficulty_distribution)

            if difficulty == 'easy':
                # Obvious temporary files
                name = random.choice([
                    f'temp{i}.tmp',
                    f'temporary_file_{i}.temp',
                    f'.~temp{i}',
                    f'swp_file_{i}.swp'
                ])
                parent_dir = '/tmp'
                size = random.randint(100, 10000)
                expected_confidence = (0.9, 0.95)
            elif difficulty == 'medium':
                # Less obvious temporary files
                name = random.choice([
                    f'cache_temp_{i}',
                    f'backup_temp_{i}.tmp',
                    f'temp_{i}.dat'
                ])
                parent_dir = '/var/tmp'
                size = random.randint(1000, 100000)
                expected_confidence = (0.7, 0.85)
            else:  # hard
                # Temporary files in unusual locations
                name = random.choice([
                    f'document_{i}.tmp',
                    f'config_{i}.temp',
                    f'important_{i}.tmp'
                ])
                parent_dir = '/home/user/documents'
                size = random.randint(50000, 1000000)
                expected_confidence = (0.4, 0.7)

            extension = os.path.splitext(name)[1].lower()
            category = 'temporary'

            file_metadata = self._create_file_metadata(
                name=name,
                parent_dir=parent_dir,
                size=size,
                extension=extension,
                days_old=random.randint(1, 365)
            )

            test_case = TestCase(
                file_metadata=file_metadata,
                expected_recommendation='delete',
                expected_category=category,
                expected_risk_level='low',
                expected_confidence_range=expected_confidence,
                protection_level=ProtectionLevel.SAFE,
                test_scenario='temporary_files',
                difficulty_level=difficulty,
                ground_truth_reasoning=f"File matches temporary pattern '{name}' in temporary directory"
            )

            cases.append(test_case)

        return cases

    def _generate_cache_file_cases(
        self,
        count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[TestCase]:
        """Generate cache file test cases."""
        cases = []

        for i in range(count):
            difficulty = self._sample_difficulty(difficulty_distribution)

            if difficulty == 'easy':
                # Obvious cache files
                name = random.choice([
                    f'cache_{i}.cache',
                    f'browser_cache_{i}.dat',
                    f'app_cache_{i}.sqlite'
                ])
                parent_dir = random.choice([
                    '/var/cache',
                    '/home/user/.cache',
                    'C:\\Users\\User\\AppData\\Local\\Temp'
                ])
                size = random.randint(1000, 50000)
                expected_confidence = (0.85, 0.95)
            elif difficulty == 'medium':
                # Cache files with less obvious names
                name = random.choice([
                    f'data_{i}.db',
                    f'storage_{i}.dat',
                    f'session_{i}'
                ])
                parent_dir = random.choice([
                    '/home/user/.local/share',
                    '/var/lib'
                ])
                size = random.randint(10000, 100000)
                expected_confidence = (0.6, 0.8)
            else:  # hard
                # Cache files in document directories
                name = random.choice([
                    f'document_cache_{i}',
                    f'config_storage_{i}.db',
                    f'user_data_{i}.cache'
                ])
                parent_dir = '/home/user/documents'
                size = random.randint(50000, 500000)
                expected_confidence = (0.3, 0.6)

            extension = os.path.splitext(name)[1].lower() or '.cache'
            category = 'cache'

            file_metadata = self._create_file_metadata(
                name=name,
                parent_dir=parent_dir,
                size=size,
                extension=extension,
                days_old=random.randint(1, 90)
            )

            test_case = TestCase(
                file_metadata=file_metadata,
                expected_recommendation='delete',
                expected_category=category,
                expected_risk_level='low',
                expected_confidence_range=expected_confidence,
                protection_level=ProtectionLevel.SAFE,
                test_scenario='cache_files',
                difficulty_level=difficulty,
                ground_truth_reasoning=f"Cache file in cache directory: {name}"
            )

            cases.append(test_case)

        return cases

    def _generate_log_file_cases(
        self,
        count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[TestCase]:
        """Generate log file test cases."""
        cases = []

        for i in range(count):
            difficulty = self._sample_difficulty(difficulty_distribution)

            if difficulty == 'easy':
                # Obvious log files
                name = random.choice([
                    f'application_{i}.log',
                    f'error_{i}.log',
                    f'system_{i}.out'
                ])
                parent_dir = '/var/log'
                size = random.randint(1000, 100000)
                expected_confidence = (0.8, 0.9)
            elif difficulty == 'medium':
                # Log files with rotation
                name = random.choice([
                    f'app.{i}.log.gz',
                    f'access_log_{i}.1',
                    f'debug_{i}.trace'
                ])
                parent_dir = random.choice(['/var/log', '/home/user/.local/share/logs'])
                size = random.randint(50000, 1000000)
                expected_confidence = (0.6, 0.8)
            else:  # hard
                # Recent or large log files
                name = random.choice([
                    f'critical_error_{i}.log',
                    f'security_audit_{i}.log',
                    f'transaction_{i}.log'
                ])
                parent_dir = '/home/user/documents'
                size = random.randint(100000, 10000000)
                days_old = random.randint(0, 7)  # Very recent
                expected_confidence = (0.3, 0.6)

            extension = os.path.splitext(name)[1].lower() or '.log'
            category = 'log'

            file_metadata = self._create_file_metadata(
                name=name,
                parent_dir=parent_dir,
                size=size,
                extension=extension,
                days_old=random.randint(1, 90)
            )

            test_case = TestCase(
                file_metadata=file_metadata,
                expected_recommendation='delete' if difficulty != 'hard' else 'manual_review',
                expected_category=category,
                expected_risk_level='low',
                expected_confidence_range=expected_confidence,
                protection_level=ProtectionLevel.REQUIRES_REVIEW if difficulty == 'hard' else ProtectionLevel.SAFE,
                test_scenario='log_files',
                difficulty_level=difficulty,
                ground_truth_reasoning=f"Log file in {parent_dir}: {name}"
            )

            cases.append(test_case)

        return cases

    def _generate_backup_file_cases(
        self,
        count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[TestCase]:
        """Generate backup file test cases."""
        cases = []

        for i in range(count):
            difficulty = self._sample_difficulty(difficulty_distribution)

            if difficulty == 'easy':
                # Obvious backup files
                name = random.choice([
                    f'document_{i}.bak',
                    f'config_{i}.old',
                    f'backup_{i}.backup'
                ])
                parent_dir = '/home/user/backups'
                size = random.randint(1000, 10000)
                expected_confidence = (0.7, 0.85)
            elif difficulty == 'medium':
                # Backup files with dates
                name = random.choice([
                    f'important_doc_20240101_{i}.bak',
                    f'config_backup_{i}.old',
                    f'system_config_{i}.save'
                ])
                parent_dir = '/home/user/documents'
                size = random.randint(10000, 100000)
                expected_confidence = (0.5, 0.7)
            else:  # hard
                # Recent or large backup files
                name = random.choice([
                    f'critical_backup_{i}.bak',
                    f'production_config_{i}.old',
                    f'database_backup_{i}.backup'
                ])
                parent_dir = '/home/user/documents'
                size = random.randint(100000, 10000000)
                days_old = random.randint(0, 30)  # Recent
                expected_confidence = (0.2, 0.5)

            extension = os.path.splitext(name)[1].lower() or '.bak'
            category = 'backup'

            file_metadata = self._create_file_metadata(
                name=name,
                parent_dir=parent_dir,
                size=size,
                extension=extension,
                days_old=random.randint(1, 365)
            )

            expected_recommendation = 'keep' if difficulty == 'hard' else 'delete'

            test_case = TestCase(
                file_metadata=file_metadata,
                expected_recommendation=expected_recommendation,
                expected_category=category,
                expected_risk_level='medium',
                expected_confidence_range=expected_confidence,
                protection_level=ProtectionLevel.REQUIRES_REVIEW if difficulty == 'hard' else ProtectionLevel.SAFE,
                test_scenario='backup_files',
                difficulty_level=difficulty,
                ground_truth_reasoning=f"Backup file: {name} (age: {file_metadata.modified_date})"
            )

            cases.append(test_case)

        return cases

    def _generate_system_file_cases(
        self,
        count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[TestCase]:
        """Generate system file test cases."""
        cases = []

        for i in range(count):
            difficulty = self._sample_difficulty(difficulty_distribution)

            if difficulty == 'easy':
                # Obvious system files
                name = random.choice([
                    f'system_{i}.dll',
                    f'kernel_{i}.sys',
                    f'library_{i}.so'
                ])
                parent_dir = random.choice([
                    '/usr/lib',
                    '/Windows/System32',
                    '/System/Library'
                ])
                size = random.randint(100000, 10000000)
                expected_confidence = (0.95, 0.99)
            elif difficulty == 'medium':
                # System configuration files
                name = random.choice([
                    f'config_{i}.conf',
                    f'system_{i}.cfg',
                    f'service_{i}.ini'
                ])
                parent_dir = random.choice(['/etc', '/etc/config.d'])
                size = random.randint(1000, 100000)
                expected_confidence = (0.8, 0.95)
            else:  # hard
                # System files in unusual locations
                name = random.choice([
                    f'user_system_{i}.dll',
                    f'custom_driver_{i}.sys',
                    f'patch_{i}.so'
                ])
                parent_dir = '/home/user/custom_software'
                size = random.randint(50000, 5000000)
                expected_confidence = (0.6, 0.8)

            extension = os.path.splitext(name)[1].lower() or '.sys'
            category = 'system'

            file_metadata = self._create_file_metadata(
                name=name,
                parent_dir=parent_dir,
                size=size,
                extension=extension,
                days_old=random.randint(30, 365)
            )

            test_case = TestCase(
                file_metadata=file_metadata,
                expected_recommendation='keep',
                expected_category=category,
                expected_risk_level='critical',
                expected_confidence_range=expected_confidence,
                protection_level=ProtectionLevel.CRITICAL,
                test_scenario='system_files',
                difficulty_level=difficulty,
                ground_truth_reasoning=f"System file in {parent_dir}: {name}"
            )

            cases.append(test_case)

        return cases

    def _generate_user_document_cases(
        self,
        count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[TestCase]:
        """Generate user document test cases."""
        cases = []

        for i in range(count):
            difficulty = self._sample_difficulty(difficulty_distribution)

            if difficulty == 'easy':
                # Obvious user documents
                name = random.choice([
                    f'report_{i}.pdf',
                    f'presentation_{i}.pptx',
                    f'spreadsheet_{i}.xlsx'
                ])
                parent_dir = '/home/user/documents'
                size = random.randint(10000, 1000000)
                expected_confidence = (0.9, 0.95)
            elif difficulty == 'medium':
                # Documents with generic names
                name = random.choice([
                    f'document_{i}.docx',
                    f'file_{i}.txt',
                    f'data_{i}.pdf'
                ])
                parent_dir = '/home/user/downloads'
                size = random.randint(5000, 500000)
                expected_confidence = (0.7, 0.9)
            else:  # hard
                # Old documents or documents in temp directories
                name = random.choice([
                    f'old_document_{i}.pdf',
                    f'draft_{i}.docx',
                    f'notes_{i}.txt'
                ])
                parent_dir = random.choice(['/tmp', '/home/user/temp'])
                size = random.randint(1000, 100000)
                days_old = random.randint(365, 1825)  # 1-5 years old
                expected_confidence = (0.4, 0.7)

            extension = os.path.splitext(name)[1].lower() or '.doc'
            category = 'document'

            file_metadata = self._create_file_metadata(
                name=name,
                parent_dir=parent_dir,
                size=size,
                extension=extension,
                days_old=random.randint(1, 365)
            )

            test_case = TestCase(
                file_metadata=file_metadata,
                expected_recommendation='keep',
                expected_category=category,
                expected_risk_level='high',
                expected_confidence_range=expected_confidence,
                protection_level=ProtectionLevel.REQUIRES_REVIEW if difficulty == 'hard' else ProtectionLevel.HIGH,
                test_scenario='user_documents',
                difficulty_level=difficulty,
                ground_truth_reasoning=f"User document: {name} in {parent_dir}"
            )

            cases.append(test_case)

        return cases

    def _generate_edge_case_tests(
        self,
        count: int,
        difficulty_distribution: Dict[str, float]
    ) -> List[TestCase]:
        """Generate edge case test cases."""
        cases = []

        edge_cases = [
            # Files with no extension
            lambda i: self._create_no_extension_case(i),
            # Files with very long names
            lambda i: self._create_long_name_case(i),
            # Files with special characters
            lambda i: self._create_special_char_case(i),
            # Files with ambiguous extensions
            lambda i: self._create_ambiguous_extension_case(i),
            # Very large files
            lambda i: self._create_large_file_case(i),
            # Very small files
            lambda i: self._create_small_file_case(i),
            # Files with future timestamps
            lambda i: self._create_future_timestamp_case(i),
            # Files with Unicode names
            lambda i: self._create_unicode_name_case(i),
            # Hidden files
            lambda i: self._create_hidden_file_case(i),
            # Files in nested directories
            lambda i: self._create_nested_directory_case(i)
        ]

        for i in range(count):
            case_generator = random.choice(edge_cases)
            test_case = case_generator(i)
            test_case.test_scenario = 'edge_cases'
            test_case.difficulty_level = 'hard'
            cases.append(test_case)

        return cases

    def _create_no_extension_case(self, i: int) -> TestCase:
        """Create a file with no extension."""
        name = f'document_{i}'
        parent_dir = '/home/user/documents'
        size = random.randint(1000, 100000)

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension='',
            days_old=random.randint(1, 365)
        )

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='manual_review',
            expected_category='unknown',
            expected_risk_level='medium',
            expected_confidence_range=(0.3, 0.6),
            protection_level=ProtectionLevel.REQUIRES_REVIEW,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning="File has no extension, requires manual review"
        )

    def _create_long_name_case(self, i: int) -> TestCase:
        """Create a file with a very long name."""
        name = 'a' * 200 + f'_{i}.tmp'
        parent_dir = '/tmp'
        size = random.randint(100, 1000)

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension='.tmp',
            days_old=random.randint(1, 30)
        )

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='delete',
            expected_category='temporary',
            expected_risk_level='low',
            expected_confidence_range=(0.6, 0.8),
            protection_level=ProtectionLevel.SAFE,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning="File has extremely long name but is in temp directory"
        )

    def _create_special_char_case(self, i: int) -> TestCase:
        """Create a file with special characters in name."""
        name = f'file@#$%^&*()_+{i}.tmp'
        parent_dir = '/tmp'
        size = random.randint(100, 1000)

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension='.tmp',
            days_old=random.randint(1, 30)
        )

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='delete',
            expected_category='temporary',
            expected_risk_level='low',
            expected_confidence_range=(0.7, 0.9),
            protection_level=ProtectionLevel.SAFE,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning="File has special characters but is in temp directory"
        )

    def _create_ambiguous_extension_case(self, i: int) -> TestCase:
        """Create a file with ambiguous extension."""
        name = random.choice([
            f'config_{i}.dat',
            f'data_{i}.file',
            f'backup_{i}.save'
        ])
        parent_dir = '/home/user/documents'
        size = random.randint(1000, 100000)

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension=os.path.splitext(name)[1],
            days_old=random.randint(1, 365)
        )

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='manual_review',
            expected_category='unknown',
            expected_risk_level='medium',
            expected_confidence_range=(0.3, 0.6),
            protection_level=ProtectionLevel.REQUIRES_REVIEW,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning=f"File has ambiguous extension '{os.path.splitext(name)[1]}'"
        )

    def _create_large_file_case(self, i: int) -> TestCase:
        """Create a very large file."""
        name = f'large_file_{i}.tmp'
        parent_dir = '/tmp'
        size = random.randint(2000000000, 5000000000)  # 2-5GB

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension='.tmp',
            days_old=random.randint(1, 30)
        )

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='manual_review',
            expected_category='temporary',
            expected_risk_level='medium',
            expected_confidence_range=(0.4, 0.7),
            protection_level=ProtectionLevel.REQUIRES_CONFIRMATION,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning="Very large file requires manual review despite being temporary"
        )

    def _create_small_file_case(self, i: int) -> TestCase:
        """Create a very small file."""
        name = f'tiny_{i}.tmp'
        parent_dir = '/tmp'
        size = random.randint(1, 100)  # 1-100 bytes

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension='.tmp',
            days_old=random.randint(1, 30)
        )

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='delete',
            expected_category='temporary',
            expected_risk_level='low',
            expected_confidence_range=(0.8, 0.95),
            protection_level=ProtectionLevel.SAFE,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning="Very small temporary file is safe to delete"
        )

    def _create_future_timestamp_case(self, i: int) -> TestCase:
        """Create a file with future timestamp."""
        name = f'future_{i}.tmp'
        parent_dir = '/tmp'
        size = random.randint(100, 1000)

        # Create metadata with future timestamp
        future_date = datetime.now() + timedelta(days=random.randint(1, 30))

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension='.tmp',
            days_old=-random.randint(1, 30)  # Negative for future date
        )
        file_metadata.modified_date = future_date.isoformat()
        file_metadata.created_date = future_date.isoformat()

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='manual_review',
            expected_category='temporary',
            expected_risk_level='medium',
            expected_confidence_range=(0.2, 0.5),
            protection_level=ProtectionLevel.REQUIRES_REVIEW,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning="File has future timestamp, requires investigation"
        )

    def _create_unicode_name_case(self, i: int) -> TestCase:
        """Create a file with Unicode characters in name."""
        name = f'файл_{i}.tmp'  # Cyrillic
        parent_dir = '/tmp'
        size = random.randint(100, 1000)

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension='.tmp',
            days_old=random.randint(1, 30)
        )

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='delete',
            expected_category='temporary',
            expected_risk_level='low',
            expected_confidence_range=(0.7, 0.9),
            protection_level=ProtectionLevel.SAFE,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning="File has Unicode name but is in temp directory"
        )

    def _create_hidden_file_case(self, i: int) -> TestCase:
        """Create a hidden file."""
        name = f'.hidden_temp_{i}.tmp'
        parent_dir = '/tmp'
        size = random.randint(100, 1000)

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension='.tmp',
            days_old=random.randint(1, 30),
            is_hidden=True
        )

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='delete',
            expected_category='temporary',
            expected_risk_level='low',
            expected_confidence_range=(0.8, 0.95),
            protection_level=ProtectionLevel.SAFE,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning="Hidden temporary file is safe to delete"
        )

    def _create_nested_directory_case(self, i: int) -> TestCase:
        """Create a file in deeply nested directory."""
        name = f'nested_{i}.tmp'
        parent_dir = '/tmp/a/b/c/d/e/f/g/h/i/j'
        size = random.randint(100, 1000)

        file_metadata = self._create_file_metadata(
            name=name,
            parent_dir=parent_dir,
            size=size,
            extension='.tmp',
            days_old=random.randint(1, 30)
        )

        return TestCase(
            file_metadata=file_metadata,
            expected_recommendation='delete',
            expected_category='temporary',
            expected_risk_level='low',
            expected_confidence_range=(0.9, 0.95),
            protection_level=ProtectionLevel.SAFE,
            test_scenario='edge_cases',
            difficulty_level='hard',
            ground_truth_reasoning="File in deeply nested temporary directory structure"
        )

    def _create_file_metadata(
        self,
        name: str,
        parent_dir: str,
        size: int,
        extension: str,
        days_old: int,
        is_hidden: bool = False,
        is_system: bool = False
    ) -> FileMetadata:
        """Create FileMetadata object."""
        base_date = datetime.now() - timedelta(days=abs(days_old))
        file_path = os.path.join(parent_dir, name)

        return FileMetadata(
            path=file_path,
            name=name,
            size_bytes=size,
            extension=extension,
            created_date=base_date.isoformat(),
            modified_date=base_date.isoformat(),
            accessed_date=base_date.isoformat(),
            parent_directory=parent_dir,
            is_hidden=is_hidden,
            is_system=is_system
        )

    def _sample_difficulty(self, distribution: Dict[str, float]) -> str:
        """Sample difficulty level from distribution."""
        rand_val = random.random()
        cumulative = 0.0

        for difficulty, prob in distribution.items():
            cumulative += prob
            if rand_val <= cumulative:
                return difficulty

        return 'medium'  # Default

    def _save_dataset(self, test_cases: List[TestCase], dataset_name: str):
        """Save dataset to file."""
        # Convert test cases to serializable format
        dataset = []
        for case in test_cases:
            case_data = {
                'file_metadata': asdict(case.file_metadata),
                'expected_recommendation': case.expected_recommendation,
                'expected_category': case.expected_category,
                'expected_risk_level': case.expected_risk_level,
                'expected_confidence_range': case.expected_confidence_range,
                'protection_level': case.protection_level.value,
                'test_scenario': case.test_scenario,
                'difficulty_level': case.difficulty_level,
                'ground_truth_reasoning': case.ground_truth_reasoning
            }
            dataset.append(case_data)

        # Save as JSON
        output_file = self.output_dir / f"{dataset_name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)

        print(f"Saved dataset '{dataset_name}' with {len(test_cases)} test cases to {output_file}")

        # Also save summary statistics
        self._save_dataset_summary(test_cases, dataset_name)

    def _save_dataset_summary(self, test_cases: List[TestCase], dataset_name: str):
        """Save dataset summary statistics."""
        summary = {
            'dataset_name': dataset_name,
            'total_cases': len(test_cases),
            'scenario_distribution': {},
            'difficulty_distribution': {},
            'recommendation_distribution': {},
            'category_distribution': {},
            'risk_level_distribution': {},
            'protection_level_distribution': {},
            'size_statistics': {},
            'age_statistics': {}
        }

        # Calculate distributions
        for case in test_cases:
            # Scenario distribution
            scenario = case.test_scenario
            summary['scenario_distribution'][scenario] = summary['scenario_distribution'].get(scenario, 0) + 1

            # Difficulty distribution
            difficulty = case.difficulty_level
            summary['difficulty_distribution'][difficulty] = summary['difficulty_distribution'].get(difficulty, 0) + 1

            # Recommendation distribution
            rec = case.expected_recommendation
            summary['recommendation_distribution'][rec] = summary['recommendation_distribution'].get(rec, 0) + 1

            # Category distribution
            category = case.expected_category
            summary['category_distribution'][category] = summary['category_distribution'].get(category, 0) + 1

            # Risk level distribution
            risk = case.expected_risk_level
            summary['risk_level_distribution'][risk] = summary['risk_level_distribution'].get(risk, 0) + 1

            # Protection level distribution
            protection = case.protection_level.value
            summary['protection_level_distribution'][protection] = summary['protection_level_distribution'].get(protection, 0) + 1

        # Calculate size statistics
        sizes = [case.file_metadata.size_bytes for case in test_cases]
        if sizes:
            summary['size_statistics'] = {
                'min_size': min(sizes),
                'max_size': max(sizes),
                'mean_size': statistics.mean(sizes),
                'median_size': statistics.median(sizes)
            }

        # Calculate age statistics
        ages = []
        for case in test_cases:
            try:
                modified_date = datetime.fromisoformat(case.file_metadata.modified_date)
                age_days = (datetime.now() - modified_date).days
                ages.append(age_days)
            except:
                pass

        if ages:
            summary['age_statistics'] = {
                'min_age_days': min(ages),
                'max_age_days': max(ages),
                'mean_age_days': statistics.mean(ages),
                'median_age_days': statistics.median(ages)
            }

        # Save summary
        summary_file = self.output_dir / f"{dataset_name}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        print(f"Saved dataset summary to {summary_file}")


def main():
    """Generate all validation datasets."""
    generator = DatasetGenerator()

    print("Generating comprehensive validation dataset...")
    comprehensive_dataset = generator.generate_comprehensive_dataset(
        num_samples=1000,
        dataset_name="comprehensive_validation"
    )

    print("Generating confidence calibration dataset...")
    confidence_dataset = generator.generate_comprehensive_dataset(
        num_samples=500,
        dataset_name="confidence_calibration"
    )

    print("Generating edge cases dataset...")
    edge_cases_dataset = generator.generate_comprehensive_dataset(
        num_samples=200,
        dataset_name="edge_cases",
        difficulty_distribution={'easy': 0.1, 'medium': 0.3, 'hard': 0.6}
    )

    print("Dataset generation complete!")


if __name__ == "__main__":
    main()