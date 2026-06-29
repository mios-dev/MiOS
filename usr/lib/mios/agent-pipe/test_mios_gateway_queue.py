#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_gateway_queue (CONV-03).
# Pure python/stdlib/dependency test, no DB required.
# AI-related: ./mios_gateway_queue.py

import asyncio
import sys
import unittest
from unittest.mock import MagicMock, patch

import mios_gateway_queue as mq

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


async def t_queue_basic():
    # Test basic put, get, and queue size
    q = mq.GatewayQueue(maxsize=10)
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    req = mq.GatewayRequest(payload={"test": "data"}, fut=fut)
    
    await q.put(req)
    check("queue: put sets size to 1", q.qsize() == 1)
    
    ret = await q.get()
    check("queue: retrieved request matches", ret == req)
    check("queue: payload content is intact", ret.payload["test"] == "data")
    
    q.task_done()


async def t_future_resolution():
    # Test future resolution
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    req = mq.GatewayRequest(payload={"test": "data"}, fut=fut)
    
    check("future: initially not done", not fut.done())
    fut.set_result({"choices": [{"message": {"content": "ok"}}]})
    check("future: becomes done", fut.done())
    res = await fut
    check("future: result content matches", res["choices"][0]["message"]["content"] == "ok")


async def t_worker_run_and_cancellation():
    # Test worker run and cancel
    with patch("mios_gateway_queue.ToolCallingAgent") as MockAgent, \
         patch("mios_gateway_queue.LiteLLMModel") as MockModel:
         
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value = "hello from agent"
        MockAgent.return_value = mock_agent_instance
        
        q = mq.GatewayQueue(maxsize=10)
        worker = mq.GatewayWorker(tools=[], endpoint="http://local:8080/v1", model_name="test-model")
        
        # Start worker as a background task
        task = asyncio.create_task(worker.run(q, concurrency=2))
        
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        req = mq.GatewayRequest(payload={"messages": [{"role": "user", "content": "hi"}]}, fut=fut)
        
        await q.put(req)
        
        # Await future
        res = await fut
        check("worker: future resolved", fut.done())
        check("worker: returns correct assistant message", res["choices"][0]["message"]["content"] == "hello from agent")
        
        # Cancel worker task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        check("worker: task cancelled cleanly", task.done())


async def t_worker_exception_handling():
    # Test worker handling exceptions from the agent
    with patch("mios_gateway_queue.ToolCallingAgent") as MockAgent, \
         patch("mios_gateway_queue.LiteLLMModel") as MockModel:
         
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.side_effect = RuntimeError("agent crash")
        MockAgent.return_value = mock_agent_instance
        
        q = mq.GatewayQueue(maxsize=10)
        worker = mq.GatewayWorker(tools=[], endpoint="http://local:8080/v1", model_name="test-model")
        
        task = asyncio.create_task(worker.run(q, concurrency=1))
        
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        req = mq.GatewayRequest(payload={"messages": [{"role": "user", "content": "hi"}]}, fut=fut)
        
        await q.put(req)
        
        try:
            await fut
            check("exception: failed to throw", False)
        except RuntimeError as e:
            check("exception: raised as future exception", str(e) == "agent crash")
            
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(t_queue_basic())
        loop.run_until_complete(t_future_resolution())
        loop.run_until_complete(t_worker_run_and_cancellation())
        loop.run_until_complete(t_worker_exception_handling())
    finally:
        loop.close()
        
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
