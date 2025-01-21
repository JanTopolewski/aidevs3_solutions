from openai import AsyncOpenAI
import asyncio

client = AsyncOpenAI(api_key = "secret_apikey")

async def get_answer_from_gpt(task):
    system_prompt = '''You are a robot whose task is to reach a goal on a map.'''

    ai_response = await client.chat.completions.create(
        model = "gpt-4o-mini",
        messages = [
            {"role":"system", "content":system_prompt},
            {"role":"user", "content": task}
        ]
    )
    return ai_response.choices[0].message.content

async def main():
    task_with_map = '''You are a robot whose task is to achieve a goal on the map by finding a way to it.

<rules>
- the map is 6 in width and 4 in height
- each location has its own address (the upper left one is 0;0, the lower right one is 3;5)
- the addresses (0;1), (1;3), (2;1), (2;3), (3;1) contain walls. You can't stand in their place, which means you have to check before each move whether you won't accidentally stand on them
- you are initially at the address (3;0)
- your target is at address (3;5)
- you can only make such moves as: UP -> decrease the first value of the address of your current position by one, DOWN -> increase the first value of the address of your current position by one, RIGHT -> increase the second value of the address of your current position by one, LEFT -> decrementing the second address value of your current position by one
- remember that you cannot make a move that will cause you to go outside the map or enter a wall
- at the beginning of your answer, write down your reasoning in steps
- at the end of your answer, list the moves to be made in tags in json format as shown in the example:
    <RESULT>
    {
    "steps": "UP, RIGHT, DOWN, LEFT"
    }
    </RESULT>
</rules>'''
    print("The result of the test program for the prompt:\n", await get_answer_from_gpt(task_with_map))

if __name__ == "__main__":
    asyncio.run(main())