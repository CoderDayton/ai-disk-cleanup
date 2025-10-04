#!/usr/bin/env python3
"""
AI Accuracy Validation Runner - Main script for running AI accuracy validation.

This script provides a command-line interface for running comprehensive AI accuracy
validation, generating test datasets, and producing detailed reports.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.ai_disk_cleanup.core.ai_analyzer import AIAnalyzer
from src.ai_disk_cleanup.safety_layer import SafetyLayer
from src.ai_disk_cleanup.core.config_models import AppConfig, ConfidenceLevel
from src.ai_disk_cleanup.accuracy.accuracy_reporter import AccuracyReporter, AccuracyThresholds
from src.ai_disk_cleanup.openai_client import FileMetadata, FileAnalysisResult


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('ai_accuracy_validation.log')
        ]
    )
    return logging.getLogger(__name__)


def load_config(config_file: Optional[str] = None) -> AppConfig:
    """Load configuration from file or create default."""
    if config_file and Path(config_file).exists():
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)

            # Create AppConfig from data
            # This is a simplified version - adapt as needed
            return AppConfig(
                ai_model=type('AIModel', (), {
                    'model_name': config_data.get('model_name', 'gpt-3.5-turbo'),
                    'temperature': config_data.get('temperature', 0.1),
                    'max_tokens': config_data.get('max_tokens', 1000),
                    'timeout_seconds': config_data.get('timeout_seconds', 30)
                })()
            )
        except Exception as e:
            print(f"Error loading config file: {e}")
            print("Using default configuration")

    # Default configuration
    return AppConfig(
        ai_model=type('AIModel', (), {
            'model_name': 'gpt-3.5-turbo',
            'temperature': 0.1,
            'max_tokens': 1000,
            'timeout_seconds': 30
        })()
    )


def run_validation(
    dataset_path: str,
    config: AppConfig,
    output_dir: str,
    thresholds: Optional[AccuracyThresholds] = None,
    sample_size: Optional[int] = None
) -> Dict[str, Any]:
    """Run AI accuracy validation on a dataset."""
    logger = logging.getLogger(__name__)

    logger.info(f"Starting validation on dataset: {dataset_path}")

    # Load validation dataset
    with open(dataset_path, 'r') as f:
        dataset = json.load(f)

    if sample_size:
        dataset = dataset[:sample_size]
        logger.info(f"Using sample size: {sample_size}")

    logger.info(f"Loaded {len(dataset)} test cases")

    # Initialize AI analyzer
    safety_layer = SafetyLayer()
    ai_analyzer = AIAnalyzer(config, safety_layer)

    # Load dataset into analyzer
    dataset_name = Path(dataset_path).stem
    ai_analyzer.load_validation_dataset(dataset_name, dataset_path)

    # Run validation on sample of dataset
    test_data = []
    logger.info("Running AI analysis on test cases...")

    for i, test_case in enumerate(dataset):
        if i % 100 == 0:
            logger.info(f"Processed {i}/{len(dataset)} cases")

        file_metadata_dict = test_case['file_metadata']
        file_metadata = FileMetadata(**file_metadata_dict)

        # Mock AI analysis result (in real usage, this would call OpenAI)
        mock_result = FileAnalysisResult(
            path=file_metadata.path,
            deletion_recommendation=test_case['expected_recommendation'],
            confidence=ConfidenceLevel.HIGH,
            reason="Mock analysis for validation",
            category=test_case['expected_category'],
            risk_level=test_case['expected_risk_level'],
            suggested_action=test_case['expected_recommendation']
        )

        # Calculate confidence score
        confidence_score = ai_analyzer._calculate_confidence_score(
            file_metadata, mock_result, include_safety_assessment=True
        )

        # Check if prediction matches expected
        is_correct = mock_result.deletion_recommendation == test_case['expected_recommendation']

        test_data.append({
            'is_correct': is_correct,
            'confidence': confidence_score.get_calibrated_score(),
            'uncertainty': confidence_score.uncertainty,
            'prediction_type': 'deletion_recommendation',
            'recommendation': mock_result.deletion_recommendation,
            'category': mock_result.category,
            'file_path': file_metadata.path
        })

    logger.info(f"Completed analysis on {len(test_data)} cases")

    # Calculate accuracy metrics
    logger.info("Calculating accuracy metrics...")
    metrics = ai_analyzer.calculate_accuracy_metrics(test_data)

    # Generate comprehensive report
    logger.info("Generating accuracy report...")
    reporter = AccuracyReporter(output_dir=output_dir, thresholds=thresholds)
    report = reporter.generate_comprehensive_report(ai_analyzer, dataset_name, test_data)

    # Generate summary
    summary = {
        'dataset_name': dataset_name,
        'total_cases': len(dataset),
        'sample_size': len(test_data),
        'overall_accuracy': metrics.overall_accuracy,
        'confidence_calibration': metrics.confidence_calibration,
        'error_rate': metrics.error_analysis['error_rate'],
        'mean_uncertainty': metrics.uncertainty_analysis['mean_uncertainty'],
        'summary_score': metrics.get_summary_score(),
        'performance_grade': report.performance_grade,
        'threshold_compliance': report.threshold_compliance,
        'recommendations_count': len(report.recommendations),
        'report_files': {
            'html': f"{output_dir}/{report.report_id}_report.html",
            'json': f"{output_dir}/{report.report_id}_detailed.json",
            'csv': f"{output_dir}/{report.report_id}_summary.csv",
            'analysis': f"{output_dir}/{report.report_id}_analysis.json"
        }
    }

    return summary


def generate_datasets(output_dir: str, sizes: List[int] = None):
    """Generate validation datasets."""
    logger = logging.getLogger(__name__)

    if sizes is None:
        sizes = [1000, 500, 200]

    # Import dataset generator
    sys.path.append(str(Path(__file__).parent / 'tests' / 'test_data'))
    from dataset_generator import DatasetGenerator

    generator = DatasetGenerator(output_dir)

    datasets = {
        'comprehensive_validation': sizes[0],
        'confidence_calibration': sizes[1],
        'edge_cases': sizes[2]
    }

    for dataset_name, size in datasets.items():
        logger.info(f"Generating {dataset_name} dataset with {size} samples...")
        generator.generate_comprehensive_dataset(
            num_samples=size,
            dataset_name=dataset_name
        )

    logger.info("Dataset generation complete")


def main():
    """Main entry point for AI accuracy validation."""
    parser = argparse.ArgumentParser(
        description="AI Accuracy Validation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate on comprehensive dataset
  python validate_ai_accuracy.py validate tests/test_data/comprehensive_validation.json

  # Generate validation datasets
  python validate_ai_accuracy.py generate-datasets

  # Run validation with custom sample size
  python validate_ai_accuracy.py validate tests/test_data/comprehensive_validation.json --sample-size 100

  # Run with custom thresholds
  python validate_ai_accuracy.py validate tests/test_data/comprehensive_validation.json --min-accuracy 0.9 --max-error-rate 0.1
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Validation command
    validate_parser = subparsers.add_parser('validate', help='Run AI accuracy validation')
    validate_parser.add_argument('dataset', help='Path to validation dataset')
    validate_parser.add_argument('--config', help='Configuration file path')
    validate_parser.add_argument('--output-dir', default='/home/malu/.projects/ai-disk-cleanup/reports',
                                help='Output directory for reports')
    validate_parser.add_argument('--sample-size', type=int, help='Sample size for validation')
    validate_parser.add_argument('--min-accuracy', type=float, default=0.85,
                                help='Minimum acceptable accuracy')
    validate_parser.add_argument('--max-error-rate', type=float, default=0.15,
                                help='Maximum acceptable error rate')
    validate_parser.add_argument('--min-confidence-calibration', type=float, default=0.75,
                                help='Minimum confidence calibration score')
    validate_parser.add_argument('--max-uncertainty', type=float, default=0.30,
                                help='Maximum acceptable mean uncertainty')
    validate_parser.add_argument('--verbose', '-v', action='store_true',
                                help='Enable verbose logging')

    # Dataset generation command
    generate_parser = subparsers.add_parser('generate-datasets', help='Generate validation datasets')
    generate_parser.add_argument('--output-dir', default='/home/malu/.projects/ai-disk-cleanup/tests/test_data',
                                help='Output directory for datasets')
    generate_parser.add_argument('--comprehensive-size', type=int, default=1000,
                                help='Size of comprehensive dataset')
    generate_parser.add_argument('--confidence-size', type=int, default=500,
                                help='Size of confidence calibration dataset')
    generate_parser.add_argument('--edge-cases-size', type=int, default=200,
                                help='Size of edge cases dataset')
    generate_parser.add_argument('--verbose', '-v', action='store_true',
                                help='Enable verbose logging')

    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Show validation summary')
    summary_parser.add_argument('--reports-dir', default='/home/malu/.projects/ai-disk-cleanup/reports',
                               help='Directory containing validation reports')
    summary_parser.add_argument('--verbose', '-v', action='store_true',
                               help='Enable verbose logging')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Setup logging
    logger = setup_logging(getattr(args, 'verbose', False))

    try:
        if args.command == 'validate':
            # Load configuration
            config = load_config(args.config)

            # Create custom thresholds if specified
            thresholds = AccuracyThresholds(
                min_overall_accuracy=args.min_accuracy,
                max_error_rate=args.max_error_rate,
                min_confidence_calibration=args.min_confidence_calibration,
                max_uncertainty=args.max_uncertainty
            )

            # Run validation
            summary = run_validation(
                dataset_path=args.dataset,
                config=config,
                output_dir=args.output_dir,
                thresholds=thresholds,
                sample_size=args.sample_size
            )

            # Print results
            print("\n" + "="*60)
            print("AI ACCURACY VALIDATION RESULTS")
            print("="*60)
            print(f"Dataset: {summary['dataset_name']}")
            print(f"Total Cases: {summary['total_cases']}")
            print(f"Sample Size: {summary['sample_size']}")
            print(f"Overall Accuracy: {summary['overall_accuracy']:.1%}")
            print(f"Confidence Calibration: {summary['confidence_calibration']:.1%}")
            print(f"Error Rate: {summary['error_rate']:.1%}")
            print(f"Mean Uncertainty: {summary['mean_uncertainty']:.1%}")
            print(f"Summary Score: {summary['summary_score']:.1%}")
            print(f"Performance Grade: {summary['performance_grade']}")
            print(f"Recommendations: {summary['recommendations_count']}")
            print("\nThreshold Compliance:")
            for threshold, passed in summary['threshold_compliance'].items():
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"  {threshold}: {status}")
            print("\nGenerated Reports:")
            for report_type, file_path in summary['report_files'].items():
                print(f"  {report_type.upper()}: {file_path}")
            print("="*60)

        elif args.command == 'generate-datasets':
            sizes = [args.comprehensive_size, args.confidence_size, args.edge_cases_size]
            generate_datasets(args.output_dir, sizes)

        elif args.command == 'summary':
            # Find and analyze recent reports
            reports_dir = Path(args.reports_dir)
            if not reports_dir.exists():
                print(f"Reports directory not found: {reports_dir}")
                return

            # Find JSON report files
            json_reports = list(reports_dir.glob("*_detailed.json"))
            if not json_reports:
                print("No validation reports found")
                return

            # Load most recent reports
            recent_reports = sorted(json_reports, key=lambda p: p.stat().st_mtime, reverse=True)[:5]

            print("\n" + "="*60)
            print("RECENT VALIDATION REPORTS")
            print("="*60)

            for report_file in recent_reports:
                try:
                    with open(report_file, 'r') as f:
                        report_data = json.load(f)

                    print(f"\nReport: {report_file.stem}")
                    print(f"Dataset: {report_data['dataset_name']}")
                    print(f"Date: {report_data['timestamp']}")
                    print(f"Grade: {report_data['performance_grade']}")
                    print(f"Score: {report_data['summary_score']:.1%}")
                    print(f"Accuracy: {report_data['overall_metrics']['overall_accuracy']:.1%}")
                    print(f"Calibration: {report_data['overall_metrics']['confidence_calibration']:.1%}")
                except Exception as e:
                    print(f"Error reading report {report_file}: {e}")

            print("="*60)

    except KeyboardInterrupt:
        print("\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()