from langchain_groq import ChatGroq
import asyncio
from mcp_use import MCPAgent, MCPClient
from dotenv import load_dotenv
load_dotenv()

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
config = {
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "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"
      }
    }
    
  }
}

async def main():
    client = MCPClient(config)
    agent = MCPAgent(llm, client)
    response = await agent.run("what is my follower count? my username is Samarth1015")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())