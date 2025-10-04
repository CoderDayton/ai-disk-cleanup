"""
AI Accuracy Reporter - Comprehensive accuracy metrics and reporting system.

This module provides comprehensive accuracy metrics calculation, visualization,
and reporting capabilities for AI analysis validation.
"""

import json
import logging
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
from dataclasses import dataclass, field
import csv
import math

from ..core.ai_analyzer import (
    AIAnalyzer,
    AccuracyMetrics,
    ConfidenceScore,
    PredictionResult,
    PredictionType
)


@dataclass
class AccuracyThresholds:
    """Thresholds for acceptable AI performance."""
    min_overall_accuracy: float = 0.85
    min_confidence_calibration: float = 0.75
    max_error_rate: float = 0.15
    min_confidence_reliability: float = 0.70
    max_uncertainty: float = 0.30
    min_recommendation_accuracy: float = 0.80


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    report_id: str
    timestamp: datetime
    dataset_name: str
    total_samples: int
    overall_metrics: AccuracyMetrics
    threshold_compliance: Dict[str, bool]
    detailed_analysis: Dict[str, Any]
    recommendations: List[str]
    performance_grade: str  # A, B, C, D, F
    summary_score: float


class AccuracyReporter:
    """
    Comprehensive accuracy reporting and analysis system.

    This class provides detailed accuracy analysis, visualization data generation,
    and comprehensive reporting for AI validation results.
    """

    def __init__(
        self,
        output_dir: str = "/home/malu/.projects/ai-disk-cleanup/reports",
        thresholds: Optional[AccuracyThresholds] = None
    ):
        """Initialize accuracy reporter."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.thresholds = thresholds or AccuracyThresholds()
        self.logger = logging.getLogger(__name__)

        # Report templates
        self.report_template = self._load_report_template()

    def _load_report_template(self) -> str:
        """Load HTML report template."""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>AI Accuracy Validation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric-card { background-color: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #007cba; }
        .grade-a { border-left-color: #28a745; }
        .grade-b { border-left-color: #ffc107; }
        .grade-c { border-left-color: #fd7e14; }
        .grade-d { border-left-color: #dc3545; }
        .grade-f { border-left-color: #6f42c1; }
        .threshold-pass { color: #28a745; }
        .threshold-fail { color: #dc3545; }
        .chart-container { margin: 20px 0; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .recommendation { background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .summary-score { font-size: 24px; font-weight: bold; text-align: center; margin: 20px 0; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="header">
        <h1>AI Accuracy Validation Report</h1>
        <p><strong>Dataset:</strong> {dataset_name}</p>
        <p><strong>Generated:</strong> {timestamp}</p>
        <p><strong>Report ID:</strong> {report_id}</p>
    </div>

    <div class="summary-score grade-{grade_class}">
        Overall Score: {summary_score:.1%} (Grade: {performance_grade})
    </div>

    <div class="metrics">
        <div class="metric-card">
            <h3>Overall Accuracy</h3>
            <p style="font-size: 24px; color: #007cba;">{overall_accuracy:.1%}</p>
            <p class="{accuracy_class}">Threshold: {min_overall_accuracy:.1%}</p>
        </div>

        <div class="metric-card">
            <h3>Confidence Calibration</h3>
            <p style="font-size: 24px; color: #007cba;">{confidence_calibration:.1%}</p>
            <p class="{calibration_class}">Threshold: {min_confidence_calibration:.1%}</p>
        </div>

        <div class="metric-card">
            <h3>Error Rate</h3>
            <p style="font-size: 24px; color: #dc3545;">{error_rate:.1%}</p>
            <p class="{error_class}">Max: {max_error_rate:.1%}</p>
        </div>

        <div class="metric-card">
            <h3>Mean Uncertainty</h3>
            <p style="font-size: 24px; color: #007cba;">{mean_uncertainty:.1%}</p>
            <p class="{uncertainty_class}">Max: {max_uncertainty:.1%}</p>
        </div>
    </div>

    <h2>Threshold Compliance</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
            <th>Threshold</th>
            <th>Status</th>
        </tr>
        {threshold_table_rows}
    </table>

    <h2>Confidence Distribution</h2>
    <div class="chart-container">
        <canvas id="confidenceChart" width="400" height="200"></canvas>
    </div>

    <h2>Calibration Curve</h2>
    <div class="chart-container">
        <canvas id="calibrationChart" width="400" height="200"></canvas>
    </div>

    <h2>Recommendation Accuracy</h2>
    <div class="chart-container">
        <canvas id="recommendationChart" width="400" height="200"></canvas>
    </div>

    <h2>Recommendations</h2>
    {recommendations_html}

    <h2>Detailed Analysis</h2>
    <pre>{detailed_analysis_json}</pre>

    <script>
        // Confidence Distribution Chart
        const confidenceCtx = document.getElementById('confidenceChart').getContext('2d');
        new Chart(confidenceCtx, {{
            type: 'bar',
            data: {{
                labels: {confidence_labels},
                datasets: [{{
                    label: 'Count',
                    data: {confidence_data},
                    backgroundColor: '#007cba'
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Confidence Score Distribution'
                    }}
                }}
            }}
        }});

        // Calibration Curve Chart
        const calibrationCtx = document.getElementById('calibrationChart').getContext('2d');
        new Chart(calibrationCtx, {{
            type: 'scatter',
            data: {{
                datasets: [{{
                    label: 'Calibration Curve',
                    data: {calibration_data},
                    backgroundColor: '#007cba'
                }}, {{
                    label: 'Perfect Calibration',
                    data: Array.from({{length: 11}}, (_, i) => ({{x: i/10, y: i/10}})),
                    type: 'line',
                    borderColor: '#dc3545',
                    borderDash: [5, 5]
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: 'Predicted Confidence'
                        }},
                        min: 0,
                        max: 1
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: 'Actual Accuracy'
                        }},
                        min: 0,
                        max: 1
                    }}
                }},
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Confidence Calibration Curve'
                    }}
                }}
            }}
        }});

        // Recommendation Accuracy Chart
        const recommendationCtx = document.getElementById('recommendationChart').getContext('2d');
        new Chart(recommendationCtx, {{
            type: 'bar',
            data: {{
                labels: {recommendation_labels},
                datasets: [{{
                    label: 'Accuracy',
                    data: {recommendation_data},
                    backgroundColor: '#28a745'
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 1,
                        ticks: {{
                            callback: function(value) {{
                                return (value * 100) + '%';
                            }}
                        }}
                    }}
                }},
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Accuracy by Recommendation Type'
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
        """

    def generate_comprehensive_report(
        self,
        ai_analyzer: AIAnalyzer,
        dataset_name: str,
        test_data: Optional[List[Dict[str, Any]]] = None
    ) -> ValidationReport:
        """
        Generate a comprehensive accuracy validation report.

        Args:
            ai_analyzer: AI analyzer with validation results
            dataset_name: Name of the dataset being validated
            test_data: Optional test data for analysis

        Returns:
            ValidationReport with comprehensive analysis
        """
        # Get accuracy metrics
        if dataset_name in ai_analyzer.accuracy_cache:
            metrics = ai_analyzer.accuracy_cache[dataset_name]
        elif test_data:
            metrics = ai_analyzer.calculate_accuracy_metrics(test_data)
        else:
            raise ValueError("No accuracy data available for report generation")

        # Calculate threshold compliance
        threshold_compliance = self._calculate_threshold_compliance(metrics)

        # Generate detailed analysis
        detailed_analysis = self._generate_detailed_analysis(metrics, ai_analyzer)

        # Generate recommendations
        recommendations = self._generate_recommendations(metrics, threshold_compliance)

        # Calculate performance grade
        performance_grade = self._calculate_performance_grade(metrics, threshold_compliance)

        # Create report
        report = ValidationReport(
            report_id=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            dataset_name=dataset_name,
            total_samples=len(test_data) if test_data else 0,
            overall_metrics=metrics,
            threshold_compliance=threshold_compliance,
            detailed_analysis=detailed_analysis,
            recommendations=recommendations,
            performance_grade=performance_grade,
            summary_score=metrics.get_summary_score()
        )

        # Save reports
        self._save_reports(report)

        return report

    def _calculate_threshold_compliance(self, metrics: AccuracyMetrics) -> Dict[str, bool]:
        """Calculate compliance with accuracy thresholds."""
        compliance = {
            'overall_accuracy': metrics.overall_accuracy >= self.thresholds.min_overall_accuracy,
            'confidence_calibration': metrics.confidence_calibration >= self.thresholds.min_confidence_calibration,
            'error_rate': metrics.error_analysis['error_rate'] <= self.thresholds.max_error_rate,
            'uncertainty': metrics.uncertainty_analysis['mean_uncertainty'] <= self.thresholds.max_uncertainty
        }

        # Check recommendation accuracy thresholds
        for rec_type, accuracy in metrics.recommendation_accuracy.items():
            compliance[f'recommendation_accuracy_{rec_type}'] = accuracy >= self.thresholds.min_recommendation_accuracy

        return compliance

    def _generate_detailed_analysis(
        self,
        metrics: AccuracyMetrics,
        ai_analyzer: AIAnalyzer
    ) -> Dict[str, Any]:
        """Generate detailed analysis of metrics."""
        analysis = {
            'summary_statistics': {
                'total_predictions': len(ai_analyzer.prediction_history),
                'summary_score': metrics.get_summary_score(),
                'performance_tier': self._get_performance_tier(metrics.get_summary_score())
            },
            'confidence_analysis': {
                'distribution': metrics.confidence_distribution,
                'calibration_quality': metrics.confidence_calibration,
                'mean_confidence': self._calculate_mean_confidence(ai_analyzer),
                'confidence_stability': self._calculate_confidence_stability(ai_analyzer)
            },
            'error_analysis': {
                'error_patterns': metrics.error_analysis['error_patterns'],
                'error_rate_by_confidence': self._analyze_errors_by_confidence(ai_analyzer),
                'common_error_scenarios': self._identify_common_error_scenarios(ai_analyzer)
            },
            'prediction_type_analysis': {
                'accuracy_by_type': {
                    pred_type.value: accuracy
                    for pred_type, accuracy in metrics.prediction_accuracy_by_type.items()
                },
                'type_distribution': self._calculate_prediction_type_distribution(ai_analyzer)
            },
            'uncertainty_analysis': {
                'mean_uncertainty': metrics.uncertainty_analysis['mean_uncertainty'],
                'uncertainty_calibration': metrics.uncertainty_analysis['uncertainty_calibration'],
                'high_uncertainty_proportion': self._calculate_high_uncertainty_proportion(ai_analyzer)
            },
            'recommendation_analysis': {
                'accuracy_by_recommendation': metrics.recommendation_accuracy,
                'recommendation_distribution': self._calculate_recommendation_distribution(ai_analyzer)
            }
        }

        return analysis

    def _generate_recommendations(
        self,
        metrics: AccuracyMetrics,
        threshold_compliance: Dict[str, bool]
    ) -> List[str]:
        """Generate actionable recommendations based on metrics."""
        recommendations = []

        # Accuracy recommendations
        if not threshold_compliance.get('overall_accuracy', False):
            recommendations.append(
                f"Overall accuracy ({metrics.overall_accuracy:.1%}) is below threshold. "
                "Consider increasing training data or adjusting model parameters."
            )

        # Calibration recommendations
        if not threshold_compliance.get('confidence_calibration', False):
            recommendations.append(
                f"Confidence calibration ({metrics.confidence_calibration:.1%}) needs improvement. "
                "Implement better confidence estimation or temperature scaling."
            )

        # Error rate recommendations
        if not threshold_compliance.get('error_rate', False):
            recommendations.append(
                f"Error rate ({metrics.error_analysis['error_rate']:.1%}) is too high. "
                "Review error patterns and improve edge case handling."
            )

        # Uncertainty recommendations
        if not threshold_compliance.get('uncertainty', False):
            recommendations.append(
                f"Mean uncertainty ({metrics.uncertainty_analysis['mean_uncertainty']:.1%}) is too high. "
                "Improve model confidence or provide more training data."
            )

        # Specific pattern recommendations
        error_patterns = metrics.error_analysis.get('error_patterns', {})
        if error_patterns:
            most_common_error = max(error_patterns, key=error_patterns.get)
            recommendations.append(
                f"Most common errors occur in '{most_common_error}' category. "
                f"Focus improvement efforts on this file type."
            )

        # Confidence distribution recommendations
        confidence_dist = metrics.confidence_distribution
        total_predictions = sum(confidence_dist.values())
        if total_predictions > 0:
            high_confidence_ratio = (confidence_dist.get('high', 0) + confidence_dist.get('very_high', 0)) / total_predictions
            if high_confidence_ratio < 0.7:
                recommendations.append(
                    "Low proportion of high-confidence predictions. "
                    "Consider improving model confidence or adjusting thresholds."
                )

        # Calibration curve analysis
        calibration_data = metrics.calibration_curve_data
        if calibration_data:
            # Check for systematic over/under confidence
            overconfidence = any(conf > acc + 0.1 for conf, acc in calibration_data)
            underconfidence = any(conf < acc - 0.1 for conf, acc in calibration_data)

            if overconfidence:
                recommendations.append("Model shows signs of overconfidence. Implement confidence scaling.")
            if underconfidence:
                recommendations.append("Model shows signs of underconfidence. Consider confidence boosting.")

        # Add positive feedback if performance is good
        if all(threshold_compliance.values()):
            recommendations.append("Excellent performance! All thresholds are met. Maintain current model quality.")

        return recommendations

    def _calculate_performance_grade(
        self,
        metrics: AccuracyMetrics,
        threshold_compliance: Dict[str, bool]
    ) -> str:
        """Calculate overall performance grade."""
        score = metrics.get_summary_score()

        if score >= 0.95 and all(threshold_compliance.values()):
            return "A"
        elif score >= 0.85 and sum(threshold_compliance.values()) >= len(threshold_compliance) * 0.9:
            return "B"
        elif score >= 0.75 and sum(threshold_compliance.values()) >= len(threshold_compliance) * 0.8:
            return "C"
        elif score >= 0.65 and sum(threshold_compliance.values()) >= len(threshold_compliance) * 0.7:
            return "D"
        else:
            return "F"

    def _save_reports(self, report: ValidationReport):
        """Save reports in multiple formats."""
        # Save JSON report
        self._save_json_report(report)

        # Save HTML report
        self._save_html_report(report)

        # Save CSV summary
        self._save_csv_summary(report)

        # Save detailed analysis
        self._save_detailed_analysis(report)

    def _save_json_report(self, report: ValidationReport):
        """Save detailed JSON report."""
        report_data = {
            'report_id': report.report_id,
            'timestamp': report.timestamp.isoformat(),
            'dataset_name': report.dataset_name,
            'total_samples': report.total_samples,
            'summary_score': report.summary_score,
            'performance_grade': report.performance_grade,
            'overall_metrics': {
                'overall_accuracy': report.overall_metrics.overall_accuracy,
                'confidence_calibration': report.overall_metrics.confidence_calibration,
                'prediction_accuracy_by_type': {
                    pred_type.value: accuracy
                    for pred_type, accuracy in report.overall_metrics.prediction_accuracy_by_type.items()
                },
                'confidence_distribution': report.overall_metrics.confidence_distribution,
                'error_analysis': report.overall_metrics.error_analysis,
                'uncertainty_analysis': report.overall_metrics.uncertainty_analysis,
                'recommendation_accuracy': report.overall_metrics.recommendation_accuracy
            },
            'threshold_compliance': report.threshold_compliance,
            'detailed_analysis': report.detailed_analysis,
            'recommendations': report.recommendations
        }

        output_file = self.output_dir / f"{report.report_id}_detailed.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"JSON report saved: {output_file}")

    def _save_html_report(self, report: ValidationReport):
        """Save HTML visualization report."""
        # Prepare template variables
        template_vars = self._prepare_html_template_vars(report)

        # Generate HTML
        html_content = self.report_template.format(**template_vars)

        output_file = self.output_dir / f"{report.report_id}_report.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.logger.info(f"HTML report saved: {output_file}")

    def _prepare_html_template_vars(self, report: ValidationReport) -> Dict[str, Any]:
        """Prepare variables for HTML template."""
        metrics = report.overall_metrics

        # Threshold compliance classes
        accuracy_class = "threshold-pass" if report.threshold_compliance.get('overall_accuracy', False) else "threshold-fail"
        calibration_class = "threshold-pass" if report.threshold_compliance.get('confidence_calibration', False) else "threshold-fail"
        error_class = "threshold-pass" if report.threshold_compliance.get('error_rate', False) else "threshold-fail"
        uncertainty_class = "threshold-pass" if report.threshold_compliance.get('uncertainty', False) else "threshold-fail"

        # Grade class
        grade_class = f"grade-{report.performance_grade.lower()}"

        # Threshold table rows
        threshold_table_rows = ""
        thresholds = [
            ("Overall Accuracy", f"{metrics.overall_accuracy:.1%}", f"{self.thresholds.min_overall_accuracy:.1%}", report.threshold_compliance.get('overall_accuracy', False)),
            ("Confidence Calibration", f"{metrics.confidence_calibration:.1%}", f"{self.thresholds.min_confidence_calibration:.1%}", report.threshold_compliance.get('confidence_calibration', False)),
            ("Error Rate", f"{metrics.error_analysis['error_rate']:.1%}", f"{self.thresholds.max_error_rate:.1%}", report.threshold_compliance.get('error_rate', False)),
            ("Mean Uncertainty", f"{metrics.uncertainty_analysis['mean_uncertainty']:.1%}", f"{self.thresholds.max_uncertainty:.1%}", report.threshold_compliance.get('uncertainty', False))
        ]

        for metric_name, value, threshold, passed in thresholds:
            status_class = "threshold-pass" if passed else "threshold-fail"
            status_text = "✓ PASS" if passed else "✗ FAIL"
            threshold_table_rows += f"""
                <tr>
                    <td>{metric_name}</td>
                    <td>{value}</td>
                    <td>{threshold}</td>
                    <td class="{status_class}">{status_text}</td>
                </tr>
            """

        # Recommendations HTML
        recommendations_html = ""
        for i, recommendation in enumerate(report.recommendations, 1):
            recommendations_html += f'<div class="recommendation"><strong>{i}.</strong> {recommendation}</div>'

        return {
            'dataset_name': report.dataset_name,
            'timestamp': report.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'report_id': report.report_id,
            'summary_score': report.summary_score,
            'performance_grade': report.performance_grade,
            'grade_class': grade_class,
            'overall_accuracy': metrics.overall_accuracy,
            'confidence_calibration': metrics.confidence_calibration,
            'error_rate': metrics.error_analysis['error_rate'],
            'mean_uncertainty': metrics.uncertainty_analysis['mean_uncertainty'],
            'min_overall_accuracy': self.thresholds.min_overall_accuracy,
            'min_confidence_calibration': self.thresholds.min_confidence_calibration,
            'max_error_rate': self.thresholds.max_error_rate,
            'max_uncertainty': self.thresholds.max_uncertainty,
            'accuracy_class': accuracy_class,
            'calibration_class': calibration_class,
            'error_class': error_class,
            'uncertainty_class': uncertainty_class,
            'threshold_table_rows': threshold_table_rows,
            'recommendations_html': recommendations_html,
            'detailed_analysis_json': json.dumps(report.detailed_analysis, indent=2),
            'confidence_labels': list(metrics.confidence_distribution.keys()),
            'confidence_data': list(metrics.confidence_distribution.values()),
            'calibration_data': [{'x': conf, 'y': acc} for conf, acc in metrics.calibration_curve_data],
            'recommendation_labels': list(metrics.recommendation_accuracy.keys()),
            'recommendation_data': list(metrics.recommendation_accuracy.values())
        }

    def _save_csv_summary(self, report: ValidationReport):
        """Save CSV summary report."""
        summary_file = self.output_dir / f"{report.report_id}_summary.csv"

        with open(summary_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(['Metric', 'Value', 'Threshold', 'Status'])

            # Metrics
            writer.writerow([
                'Overall Accuracy',
                f"{report.overall_metrics.overall_accuracy:.3f}",
                f"{self.thresholds.min_overall_accuracy:.3f}",
                'PASS' if report.threshold_compliance.get('overall_accuracy', False) else 'FAIL'
            ])

            writer.writerow([
                'Confidence Calibration',
                f"{report.overall_metrics.confidence_calibration:.3f}",
                f"{self.thresholds.min_confidence_calibration:.3f}",
                'PASS' if report.threshold_compliance.get('confidence_calibration', False) else 'FAIL'
            ])

            writer.writerow([
                'Error Rate',
                f"{report.overall_metrics.error_analysis['error_rate']:.3f}",
                f"{self.thresholds.max_error_rate:.3f}",
                'PASS' if report.threshold_compliance.get('error_rate', False) else 'FAIL'
            ])

            writer.writerow([
                'Mean Uncertainty',
                f"{report.overall_metrics.uncertainty_analysis['mean_uncertainty']:.3f}",
                f"{self.thresholds.max_uncertainty:.3f}",
                'PASS' if report.threshold_compliance.get('uncertainty', False) else 'FAIL'
            ])

            writer.writerow(['Summary Score', f"{report.summary_score:.3f}", 'N/A', 'N/A'])
            writer.writerow(['Performance Grade', report.performance_grade, 'N/A', 'N/A'])

        self.logger.info(f"CSV summary saved: {summary_file}")

    def _save_detailed_analysis(self, report: ValidationReport):
        """Save detailed analysis report."""
        analysis_file = self.output_dir / f"{report.report_id}_analysis.json"

        detailed_data = {
            'confidence_analysis': report.detailed_analysis.get('confidence_analysis', {}),
            'error_analysis': report.detailed_analysis.get('error_analysis', {}),
            'prediction_type_analysis': report.detailed_analysis.get('prediction_type_analysis', {}),
            'uncertainty_analysis': report.detailed_analysis.get('uncertainty_analysis', {}),
            'recommendation_analysis': report.detailed_analysis.get('recommendation_analysis', {}),
            'calibration_curve_data': report.overall_metrics.calibration_curve_data,
            'threshold_compliance_details': report.threshold_compliance
        }

        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Detailed analysis saved: {analysis_file}")

    def _get_performance_tier(self, score: float) -> str:
        """Get performance tier based on score."""
        if score >= 0.95:
            return "Excellent"
        elif score >= 0.85:
            return "Good"
        elif score >= 0.75:
            return "Satisfactory"
        elif score >= 0.65:
            return "Needs Improvement"
        else:
            return "Poor"

    def _calculate_mean_confidence(self, ai_analyzer: AIAnalyzer) -> float:
        """Calculate mean confidence from prediction history."""
        if not ai_analyzer.confidence_history:
            return 0.0

        confidences = [conf.get_calibrated_score() for conf in ai_analyzer.confidence_history]
        return statistics.mean(confidences)

    def _calculate_confidence_stability(self, ai_analyzer: AIAnalyzer) -> float:
        """Calculate confidence stability (inverse of variance)."""
        if len(ai_analyzer.confidence_history) < 2:
            return 1.0

        confidences = [conf.get_calibrated_score() for conf in ai_analyzer.confidence_history]
        variance = statistics.variance(confidences)
        return 1.0 / (1.0 + variance)  # Convert to stability score

    def _analyze_errors_by_confidence(self, ai_analyzer: AIAnalyzer) -> Dict[str, float]:
        """Analyze error rates by confidence level."""
        errors_by_confidence = {'low': [], 'medium': [], 'high': []}

        for prediction in ai_analyzer.prediction_history:
            if prediction.is_correct is not None:
                conf = prediction.confidence_score.get_calibrated_score()
                if conf < 0.4:
                    errors_by_confidence['low'].append(not prediction.is_correct)
                elif conf < 0.7:
                    errors_by_confidence['medium'].append(not prediction.is_correct)
                else:
                    errors_by_confidence['high'].append(not prediction.is_correct)

        # Calculate error rates
        error_rates = {}
        for level, errors in errors_by_confidence.items():
            if errors:
                error_rates[level] = statistics.mean(errors)
            else:
                error_rates[level] = 0.0

        return error_rates

    def _identify_common_error_scenarios(self, ai_analyzer: AIAnalyzer) -> List[Dict[str, Any]]:
        """Identify common error scenarios."""
        error_scenarios = {}

        for prediction in ai_analyzer.prediction_history:
            if not prediction.is_correct and prediction.metadata:
                # Create scenario key from metadata
                scenario_parts = []
                if 'file_category' in prediction.metadata:
                    scenario_parts.append(f"category:{prediction.metadata['file_category']}")
                if 'risk_level' in prediction.metadata:
                    scenario_parts.append(f"risk:{prediction.metadata['risk_level']}")

                if scenario_parts:
                    scenario_key = " | ".join(scenario_parts)
                    if scenario_key not in error_scenarios:
                        error_scenarios[scenario_key] = 0
                    error_scenarios[scenario_key] += 1

        # Sort by frequency and return top scenarios
        sorted_scenarios = sorted(error_scenarios.items(), key=lambda x: x[1], reverse=True)
        return [{'scenario': scenario, 'count': count} for scenario, count in sorted_scenarios[:5]]

    def _calculate_prediction_type_distribution(self, ai_analyzer: AIAnalyzer) -> Dict[str, int]:
        """Calculate distribution of prediction types."""
        distribution = {}

        for prediction in ai_analyzer.prediction_history:
            pred_type = prediction.prediction_type.value
            distribution[pred_type] = distribution.get(pred_type, 0) + 1

        return distribution

    def _calculate_high_uncertainty_proportion(self, ai_analyzer: AIAnalyzer) -> float:
        """Calculate proportion of predictions with high uncertainty."""
        if not ai_analyzer.confidence_history:
            return 0.0

        high_uncertainty_count = sum(
            1 for conf in ai_analyzer.confidence_history
            if conf.uncertainty > 0.3
        )

        return high_uncertainty_count / len(ai_analyzer.confidence_history)

    def _calculate_recommendation_distribution(self, ai_analyzer: AIAnalyzer) -> Dict[str, int]:
        """Calculate distribution of recommendation types."""
        distribution = {}

        for prediction in ai_analyzer.prediction_history:
            if 'recommendation' in prediction.metadata:
                rec = prediction.metadata['recommendation']
                distribution[rec] = distribution.get(rec, 0) + 1

        return distribution

    def generate_trend_report(
        self,
        reports: List[ValidationReport],
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate trend analysis across multiple reports.

        Args:
            reports: List of validation reports to analyze
            output_file: Optional output file for the trend report

        Returns:
            Trend analysis data
        """
        if len(reports) < 2:
            raise ValueError("Need at least 2 reports for trend analysis")

        # Sort reports by timestamp
        reports.sort(key=lambda r: r.timestamp)

        # Calculate trends
        trend_data = {
            'time_series': {
                'timestamps': [r.timestamp.isoformat() for r in reports],
                'summary_scores': [r.summary_score for r in reports],
                'overall_accuracy': [r.overall_metrics.overall_accuracy for r in reports],
                'confidence_calibration': [r.overall_metrics.confidence_calibration for r in reports],
                'error_rates': [r.overall_metrics.error_analysis['error_rate'] for r in reports],
                'mean_uncertainty': [r.overall_metrics.uncertainty_analysis['mean_uncertainty'] for r in reports]
            },
            'trend_analysis': {
                'summary_score_trend': self._calculate_trend([r.summary_score for r in reports]),
                'accuracy_trend': self._calculate_trend([r.overall_metrics.overall_accuracy for r in reports]),
                'calibration_trend': self._calculate_trend([r.overall_metrics.confidence_calibration for r in reports]),
                'error_rate_trend': self._calculate_trend([r.overall_metrics.error_analysis['error_rate'] for r in reports]),
                'uncertainty_trend': self._calculate_trend([r.overall_metrics.uncertainty_analysis['mean_uncertainty'] for r in reports])
            },
            'grade_distribution': self._calculate_grade_distribution(reports),
            'threshold_compliance_trends': self._calculate_threshold_compliance_trends(reports)
        }

        # Save trend report if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(trend_data, f, indent=2, ensure_ascii=False)

        return trend_data

    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend statistics for a series of values."""
        if len(values) < 2:
            return {'direction': 'stable', 'slope': 0.0, 'change_percent': 0.0}

        # Calculate linear trend
        n = len(values)
        x_values = list(range(n))

        # Simple linear regression
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(values)

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        # Determine direction
        if abs(slope) < 0.01:
            direction = 'stable'
        elif slope > 0:
            direction = 'improving'
        else:
            direction = 'declining'

        # Calculate percentage change
        if values[0] != 0:
            change_percent = ((values[-1] - values[0]) / values[0]) * 100
        else:
            change_percent = 0.0

        return {
            'direction': direction,
            'slope': slope,
            'change_percent': change_percent,
            'start_value': values[0],
            'end_value': values[-1]
        }

    def _calculate_grade_distribution(self, reports: List[ValidationReport]) -> Dict[str, int]:
        """Calculate distribution of performance grades."""
        distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}

        for report in reports:
            grade = report.performance_grade
            if grade in distribution:
                distribution[grade] += 1

        return distribution

    def _calculate_threshold_compliance_trends(self, reports: List[ValidationReport]) -> Dict[str, Any]:
        """Calculate trends in threshold compliance."""
        compliance_trends = {}

        # Get all unique threshold keys
        all_thresholds = set()
        for report in reports:
            all_thresholds.update(report.threshold_compliance.keys())

        for threshold in all_thresholds:
            compliance_values = []
            for report in reports:
                compliance_values.append(1.0 if report.threshold_compliance.get(threshold, False) else 0.0)

            if len(compliance_values) > 1:
                trend = self._calculate_trend(compliance_values)
                compliance_trends[threshold] = trend

        return compliance_trends