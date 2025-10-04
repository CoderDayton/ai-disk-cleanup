# Performance Testing Suite

This directory contains comprehensive performance tests for the AI Disk Cleanup tool, validating API efficiency, cost control, and system performance against specified requirements.

## Performance Requirements (SDD)

### API Efficiency
- **Target**: <3 second average OpenAI API response time
- **Validation**: Response time measurement across various load conditions
- **Acceptance Criteria**: Average response time <3s, maximum response time <5s

### Cost Control
- **Target**: <$0.10 average cost per session
- **Validation**: Cost tracking and limit enforcement
- **Acceptance Criteria**: Session cost never exceeds $0.10, cost optimization through batching

### Batching Optimization
- **Target**: Intelligent batching for API efficiency
- **Validation**: Batch size optimization and content efficiency
- **Acceptance Criteria**: Optimal batch sizes, minimal API calls, efficient content transmission

### Cache Performance
- **Target**: High cache hit rates and efficient memory usage
- **Validation**: Cache hit rate >80%, memory efficiency
- **Acceptance Criteria**: Hit rate >80%, memory per entry <200KB

### Large File Set Performance
- **Target**: Efficient processing of large file sets
- **Validation**: Throughput >10 files/second, performance degradation analysis
- **Acceptance Criteria**: Linear scaling, minimal degradation, reasonable memory usage

### Memory Usage Optimization
- **Target**: Efficient memory usage with no leaks
- **Validation**: Memory leak detection, efficiency analysis
- **Acceptance Criteria**: No memory leaks, <100KB per file, reasonable total usage

## Test Structure

### Core Test Files

#### `test_api_efficiency.py`
Main performance test suite containing:
- **API Response Time Performance**: Validates <3 second response time target
- **Cost Control Validation**: Tests cost tracking and $0.10 limit enforcement
- **Batching Optimization Efficiency**: Tests intelligent batching strategies
- **Cache Performance Optimization**: Validates cache hit rates and memory efficiency
- **Large File Set Performance**: Tests performance with large file sets
- **Memory Usage Optimization**: Tests memory efficiency and leak detection

#### `conftest.py`
Shared test configuration and fixtures:
- Performance test configuration
- Mock OpenAI client factories
- File metadata generators
- Memory monitoring utilities
- Performance logging utilities
- Load testing framework

## Running Performance Tests

### Quick Start

```bash
# Run all performance tests
python run_performance_tests.py --all

# Run specific test categories
python run_performance_tests.py --api      # API performance tests
python run_performance_tests.py --cache    # Cache performance tests
python run_performance_tests.py --memory   # Memory usage tests
python run_performance_tests.py --load     # Load tests

# Include slow tests (for comprehensive validation)
python run_performance_tests.py --all --slow

# Generate detailed performance report
python run_performance_tests.py --all --report
```

### Running with pytest directly

```bash
# Run all performance tests
pytest tests/performance/ -m performance

# Run specific test categories
pytest tests/performance/ -m api_test
pytest tests/performance/ -m cache_test
pytest tests/performance/ -m memory_test
pytest tests/performance/ -m load_test

# Run with verbose output
pytest tests/performance/ -v -m performance

# Run with benchmark output
pytest tests/performance/ --benchmark-only
```

### Test Categories

#### API Performance Tests (`api_test`)
- Response time validation under various conditions
- Concurrent load testing
- Large batch performance
- Content optimization validation

#### Cache Performance Tests (`cache_test`)
- Cache hit rate validation
- Memory efficiency analysis
- Concurrent access performance
- Cache size optimization

#### Memory Tests (`memory_test`)
- Memory leak detection
- Memory usage efficiency
- Large file set memory analysis
- Memory optimization validation

#### Load Tests (`load_test`)
- Concurrent request handling
- Performance under load
- Scalability validation
- Resource contention analysis

## Test Fixtures and Utilities

### Mock Configurations
- `mock_app_config`: Standard application configuration for testing
- `mock_openai_client_factory`: Creates realistic OpenAI client mocks
- `mock_openai_response_factory`: Creates appropriate API responses

### Data Generators
- `sample_file_metadata_small`: Small dataset for basic testing
- `sample_file_metadata_batch`: Standard batch (50 files)
- `sample_file_metadata_large`: Large dataset (500 files)
- `file_metadata_factory`: Creates files with various patterns

### Monitoring Utilities
- `memory_monitor`: Tracks memory usage during tests
- `performance_logger`: Records performance metrics
- `cache_performance_analyzer`: Analyzes cache performance
- `load_test_runner`: Executes concurrent load tests

## Performance Benchmarks

### Response Time Benchmarks
- **Target**: <3 seconds average
- **Maximum**: <5 seconds for any single request
- **Concurrent Load**: <4 seconds average under load

### Cost Benchmarks
- **Target**: <$0.10 per session
- **Batch Efficiency**: >80% cost reduction vs individual requests
- **Request Optimization**: Minimize API calls through batching

### Throughput Benchmarks
- **Target**: >10 files/second
- **Large Sets**: Maintain throughput with 1000+ files
- **Concurrent**: Handle 5+ concurrent workers

### Memory Benchmarks
- **Per File**: <100KB memory per file processed
- **Cache Entry**: <200KB per cache entry
- **Total Usage**: <100MB for typical workloads
- **Leaks**: Zero memory leaks over 20+ iterations

## Performance Reports

### Automated Report Generation
Run tests with `--report` flag to generate detailed performance reports including:
- Test execution summary
- Performance metrics analysis
- Benchmark comparisons
- Recommendations for optimization

### Report Components
1. **Test Session Summary**: Duration, test types, environment
2. **Performance Targets**: Defined targets vs actual results
3. **Benchmark Results**: Detailed timing and resource usage
4. **Analysis**: Performance trends and patterns
5. **Recommendations**: Optimization suggestions

### Example Report Output
```json
{
  "test_session": {
    "timestamp": "2024-01-01T12:00:00",
    "duration_seconds": 120.5,
    "test_types": ["api", "cache", "memory"]
  },
  "performance_targets": {
    "api_response_time": "<3 seconds",
    "cost_per_session": "<$0.10",
    "cache_hit_rate": ">80%"
  },
  "summary": {
    "total_tests_run": 45,
    "passed_tests": 45,
    "failed_tests": 0
  }
}
```

## Performance Test Configuration

### Environment Variables
- `AI_PERFORMANCE_TEST_TIMEOUT`: Test timeout in seconds (default: 1800)
- `AI_PERFORMANCE_TEST_SLOW`: Include slow tests (default: false)
- `AI_PERFORMANCE_REPORT`: Generate detailed report (default: false)

### Test Configuration (PerformanceTestConfig)
```python
# Performance targets
TARGET_API_RESPONSE_TIME = 3.0  # seconds
TARGET_COST_PER_SESSION = 0.10   # dollars
MIN_CACHE_HIT_RATE = 0.8         # 80%
MAX_MEMORY_PER_FILE = 100 * 1024 # 100KB
MIN_THROUGHPUT_FILES_PER_SECOND = 10

# Test configuration
LARGE_FILE_SET_SIZE = 1000
CONCURRENT_WORKERS = 5
MEMORY_TEST_ITERATIONS = 20
```

## Troubleshooting

### Common Issues

#### Tests Time Out
- Increase timeout with `--timeout` parameter
- Check system resources (memory, CPU)
- Ensure no other resource-intensive processes running

#### Mock Failures
- Verify test dependencies installed: `pip install -e .[test]`
- Check OpenAI client mocking configuration
- Ensure credential store mocking works correctly

#### Memory Tests Fail
- Increase available system memory
- Close other applications
- Check for system memory leaks

#### Performance Degradation
- Verify test environment consistency
- Check for system resource contention
- Review recent code changes for performance impact

### Debug Mode
Run tests with verbose output for detailed debugging:
```bash
pytest tests/performance/ -v -s --tb=long
```

### Performance Profiling
For detailed performance analysis:
```bash
pytest tests/performance/ --benchmark-only --benchmark-sort=mean
```

## Continuous Integration

### CI Integration
Add performance tests to CI pipeline:
```yaml
- name: Run Performance Tests
  run: |
    python run_performance_tests.py --api --cache --memory --report
```

### Performance Regression Detection
- Set up automated performance monitoring
- Compare results against baseline benchmarks
- Alert on performance degradation >10%

### Performance Monitoring in Production
- Monitor API response times
- Track cost per session
- Monitor cache hit rates
- Alert on performance anomalies

## Best Practices

### Test Design
- Use realistic data and scenarios
- Test across different load conditions
- Validate both positive and negative scenarios
- Include edge cases and stress testing

### Performance Analysis
- Monitor multiple metrics (time, memory, cost)
- Analyze performance trends over time
- Correlate performance with system resources
- Document performance baselines

### Test Maintenance
- Update tests when performance requirements change
- Maintain realistic test data
- Regularly review and update benchmarks
- Keep test documentation current

### Production Monitoring
- Set up performance monitoring dashboards
- Configure alerts for performance anomalies
- Regular performance regression testing
- Document performance incidents and resolutions