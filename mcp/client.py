import asyncio
from fastmcp import Client


async def main() -> None:
    async with Client("http://127.0.0.1:8081/mcp") as client:
        tools = await client.list_tools()

        # Call a specific tool with arguments
        while True:
            query = input("Ask your question: ")
            if query == "exit":
                break
            result = await client.call_tool(
                name="mcp_query_bootcamp_materials", arguments={"user_input": query}
            )

            print("Tool Answer:", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
