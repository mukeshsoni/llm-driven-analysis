# Timing Logs Documentation

## Overview

The LLM-driven analysis system now includes comprehensive timing logs that provide detailed performance metrics for every API request. This helps in understanding where time is spent during query processing and identifying potential bottlenecks.

## Timing Breakdown Structure

The system tracks timing at multiple levels:

```
Total API Request Time
├── Processing Time
│   ├── LLM Calls Time
│   ├── Tool Calls Time
│   └── Other Processing Time
└── API Overhead Time
```

## Log Format Examples

### API Server Level (api_server.py)

When a request completes, you'll see:

```
✅ Successfully processed query for session abc-123
⏱️  Total API request time: 2.345s
   ├─ Processing time: 2.234s
   │  ├─ LLM calls: 1.523s (2 calls)
   │  ├─ Tool calls: 0.678s (3 calls)
   │  └─ Other: 0.033s
   └─ API overhead: 0.111s
```

### LLM Processor Level (llm_processor.py)

For each LLM call:
```
🤖 LLM call completed in 0.762s (finish_reason: tool_calls)
```

For tool requests:
```
🔧 LLM requested 2 tool call(s)
   └─ Tool 'run_query' completed in 0.234s
   └─ Tool 'get_schema' completed in 0.156s
```

Processing summary:
```
📊 Query processing summary:
   ├─ Total processing time: 2.234s
   ├─ LLM calls: 2 (1.523s total)
   ├─ Tool calls: 3 (0.678s total)
   └─ Tool turns: 1
```

### MCP Manager Level (mcp_manager.py)

Initialization:
```
✅ Connected to MCP server 'filesystem' in 0.123s
✅ Connected to MCP server 'sql' in 0.089s
📦 Loaded 5 total tools in 0.234s
⏱️  Total MCP initialization time: 0.456s
```

Tool calls:
```
🔧 Calling tool: run_query
   ├─ MCP call time: 0.198s
   └─ Total tool time: 0.234s
```

### SQL Server Level (mcp_server_sql.py)

Schema operations:
```
📊 Schema extraction for chinook.db completed in 0.045s (11 tables)
🔍 Schema resource for 'chinook' prepared in 0.067s
```

Query execution:
```
🔍 Running query on chinook database: SELECT COUNT(*) FROM Artist...
✅ Query executed successfully:
   ├─ Database: chinook
   ├─ Rows returned: 275
   ├─ Query execution: 0.012s
   └─ Total tool time: 0.023s
```

## Timing Metrics Explained

### 1. **Total API Request Time**
The complete end-to-end time from when the API receives the request until it sends the response.

### 2. **Processing Time**
Time spent in the LLM processor handling the query, including all LLM and tool calls.

### 3. **LLM Calls Time**
Cumulative time spent waiting for responses from the Azure OpenAI API.
- Includes network latency
- Model processing time
- Response streaming

### 4. **Tool Calls Time**
Cumulative time spent executing MCP tools:
- Database queries
- Schema retrieval
- File system operations

### 5. **Other Processing Time**
Time spent on:
- Message formatting
- Conversation history management
- Response parsing
- Internal processing logic

### 6. **API Overhead Time**
Time spent on:
- Request validation
- Response serialization
- Session management
- Middleware processing

## Performance Optimization Tips

Based on timing logs, you can optimize:

### 1. **High LLM Call Time**
- Consider caching frequently requested information
- Optimize prompts to reduce back-and-forth
- Use more specific initial queries

### 2. **High Tool Call Time**
- Optimize SQL queries (add indexes if needed)
- Cache schema information
- Batch related tool calls when possible

### 3. **High API Overhead**
- Check session storage efficiency
- Optimize middleware configuration
- Consider connection pooling

## Testing the Timing Logs

Run the included test script to see timing logs in action:

```bash
# Start the API server
python api_server.py

# In another terminal, run the timing tests
python test_timing/test_timing.py
```

The test script includes:
1. Simple queries (no tool calls)
2. Schema queries (get_schema tool)
3. SQL queries (run_query tool)
4. Complex queries (multiple tool calls)
5. Conversation with history
6. Parallel queries (load testing)

## Log Levels

- **INFO**: Main timing summaries and milestones
- **DEBUG**: Detailed timing for individual operations
- **ERROR**: Timing information when operations fail

## Configuration

Timing logs use the existing logger configuration from `logger_config.py`. To adjust log levels or formatting, modify the logger configuration.

## Example Use Cases

### 1. **Identifying Slow Queries**
Look for queries with high `Query execution` time in SQL server logs.

### 2. **Network Latency Issues**
Compare `MCP call time` vs `Query execution` time to identify network overhead.

### 3. **LLM Response Times**
Track `LLM call completed` times to monitor Azure OpenAI performance.

### 4. **System Load Testing**
Use parallel queries to see how timing changes under load.

## Monitoring Best Practices

1. **Set up log aggregation** to collect timing metrics across multiple requests
2. **Create alerts** for requests exceeding time thresholds
3. **Track percentiles** (p50, p95, p99) not just averages
4. **Correlate timing** with system metrics (CPU, memory, network)
5. **Regular benchmarking** to detect performance regressions

## Troubleshooting

### Issue: Timing seems incorrect
- Ensure all servers are time-synchronized
- Check for blocking I/O operations
- Verify async operations are properly awaited

### Issue: Missing timing information
- Check logger configuration level (should be INFO or DEBUG)
- Ensure all components are using the logger_config module
- Verify MCP servers are properly initialized

### Issue: High variance in timing
- Check for resource contention
- Monitor garbage collection pauses
- Verify database is not locked by other processes