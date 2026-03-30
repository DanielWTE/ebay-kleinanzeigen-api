# Load Testing Framework

This directory contains a comprehensive load testing framework for validating the Kleinanzeigen API performance optimizations. The framework simulates multiple concurrent users making API requests and provides detailed performance analysis.

## Features

- **Multiple Test Scenarios**: Single user, multiple users, stress testing, and mixed workloads
- **Concurrent User Simulation**: Realistic simulation of multiple users making simultaneous requests
- **Comprehensive Metrics**: Response times, success rates, throughput, and error analysis
- **Performance Reporting**: Console reports, JSON data, CSV summaries, and detailed request logs
- **Recommendations**: Actionable performance recommendations based on test results
- **Flexible Configuration**: Customizable test parameters and scenarios

## Quick Start

### Prerequisites

Make sure the API server is running:
```bash
# Start the API server
python main.py
# or
uvicorn main:app --reload
```

### Run Quick Performance Test

```bash
# Run a quick test with default settings
python tests/run_load_tests.py --quick

# Test against a different URL
python tests/run_load_tests.py --quick http://localhost:8000
```

### Run Comprehensive Test Suite

```bash
# Run all test scenarios and save results
python tests/run_load_tests.py --comprehensive
```

This will run:
1. Single user with multiple page counts (1, 5, 10, 15, 20 pages)
2. Multiple users with standard load (5 users, 5 requests each)
3. Stress test (10 users, 10 requests each)
4. Mixed workload test (8 users, 6 requests each)

Results are saved to the `load_test_results/` directory.

## Test Scenarios

### 1. Single User Multiple Pages
Tests performance with varying page counts to validate the 20-page < 3-second requirement.

```python
async with LoadTester() as tester:
    report = await tester.run_single_user_multiple_pages_test(
        page_counts=[1, 5, 10, 20],
        iterations=3
    )
```

### 2. Multiple Users Standard Load
Simulates realistic concurrent usage patterns.

```python
async with LoadTester() as tester:
    report = await tester.run_multiple_users_standard_load_test(
        user_count=5,
        requests_per_user=5
    )
```

### 3. Stress Test
High-load testing with many concurrent users and large page counts.

```python
async with LoadTester() as tester:
    report = await tester.run_stress_test(
        user_count=10,
        requests_per_user=10
    )
```

### 4. Mixed Workload
Realistic mix of different endpoints and usage patterns.

```python
async with LoadTester() as tester:
    report = await tester.run_mixed_workload_test(
        user_count=8,
        requests_per_user=6
    )
```

## Custom Testing

### Basic Usage

```python
import asyncio
from load_test import LoadTester, TestScenario

async def custom_test():
    async with LoadTester("http://localhost:8000") as tester:
        # Make individual requests
        result = await tester.make_request("/inserate", {
            "query": "laptop",
            "page_count": 10
        })
        
        # Simulate concurrent users
        user_metrics = await tester.simulate_concurrent_users(
            user_count=3,
            requests_per_user=5,
            scenario=TestScenario.MIXED_WORKLOAD
        )

asyncio.run(custom_test())
```

### Performance Validation

```python
async def validate_20_page_requirement():
    async with LoadTester() as tester:
        # Test 20-page requests multiple times
        results = []
        for i in range(5):
            result = await tester.make_request("/inserate", {
                "query": "smartphone",
                "page_count": 20
            })
            results.append(result)
        
        # Check if all requests completed in under 3 seconds
        avg_time = sum(r.response_time for r in results if r.success) / len([r for r in results if r.success])
        print(f"Average 20-page response time: {avg_time:.2f}s")
        print(f"Requirement met: {avg_time < 3.0}")
```

## Report Generation

The framework generates multiple types of reports:

### Console Report
Human-readable summary displayed in the terminal:
```
================================================================================
LOAD TEST REPORT - MULTIPLE_USERS_STANDARD_LOAD
================================================================================

TEST OVERVIEW
----------------------------------------
Scenario: multiple_users_standard_load
Start Time: 2024-01-15 14:30:25
End Time: 2024-01-15 14:31:45
Total Duration: 80.23 seconds
Concurrent Users: 5

REQUEST STATISTICS
----------------------------------------
Total Requests: 25
Successful Requests: 24
Failed Requests: 1
Success Rate: 96.00%
Error Rate: 4.00%
Requests per Second: 0.31
```

### JSON Report
Complete data in JSON format for programmatic analysis:
```json
{
  "scenario": "multiple_users_standard_load",
  "total_requests": 25,
  "successful_requests": 24,
  "average_response_time": 2.45,
  "recommendations": [
    "Performance looks good! All metrics are within acceptable ranges."
  ]
}
```

### CSV Summary
Metrics summary for spreadsheet analysis:
```csv
Metric,Value,Unit
Scenario,multiple_users_standard_load,
Total Duration,80.23,seconds
Success Rate,96.00,%
Average Response Time,2.450,seconds
```

## Performance Targets

The framework validates against these performance targets:

- **20-page requests**: Must complete in under 3 seconds
- **Success rate**: Should be above 95% for standard load
- **Concurrent requests**: System should handle 5+ simultaneous users
- **Error rate**: Should be below 5% under normal conditions

## Command Line Options

```bash
# Available options
python tests/run_load_tests.py --help

# Run specific test types
python tests/run_load_tests.py --quick           # Quick performance test
python tests/run_load_tests.py --individual     # Individual scenario examples
python tests/run_load_tests.py --comprehensive  # Full test suite
python tests/run_load_tests.py --validation     # Performance validation
python tests/run_load_tests.py --custom         # Custom test patterns
python tests/run_load_tests.py --all           # All test types

# Specify different API URL
python tests/run_load_tests.py --comprehensive https://api.example.com
```

## Output Files

When running comprehensive tests, results are saved to `load_test_results/`:

- `{scenario}_{timestamp}_report.txt` - Human-readable report
- `{scenario}_{timestamp}_data.json` - Complete test data
- `{scenario}_{timestamp}_summary.csv` - Metrics summary
- `{scenario}_{timestamp}_requests.csv` - Individual request details

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Ensure the API server is running
   - Check the base URL is correct
   - Verify network connectivity

2. **High Error Rates**
   - Check server logs for errors
   - Reduce concurrent user count
   - Increase request timeouts

3. **Slow Performance**
   - Monitor server resource usage
   - Check browser context pool settings
   - Verify database performance

### Debug Mode

For detailed debugging, modify the test script to include more logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run tests with debug output
```

## Integration with CI/CD

The framework can be integrated into CI/CD pipelines:

```bash
# Example CI script
#!/bin/bash
set -e

# Start API server in background
python main.py &
API_PID=$!

# Wait for server to start
sleep 5

# Run performance validation
python tests/run_load_tests.py --validation

# Check if performance targets were met
if [ $? -eq 0 ]; then
    echo "Performance tests passed"
else
    echo "Performance tests failed"
    exit 1
fi

# Clean up
kill $API_PID
```

## Contributing

When adding new test scenarios:

1. Add the scenario to the `TestScenario` enum
2. Implement the test logic in the `LoadTester` class
3. Add appropriate recommendations in `_generate_recommendations`
4. Update this README with usage examples

## Requirements

The load testing framework requires:
- Python 3.7+
- aiohttp (for HTTP requests)
- asyncio (for concurrent operations)
- Standard library modules: statistics, json, csv, datetime