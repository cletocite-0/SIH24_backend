import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])


class Agent:
    def __init__(
        self,
        agent_name,
        agent_prompt,
        agent_model,
        tools,
        streaming=False,
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    ):
        self.agent_name = agent_name
        self.agent_prompt = agent_prompt
        self.agent_model = agent_model
        self.streaming = streaming
        self.tools = tools
        self.generation_config = {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_output_tokens": max_output_tokens,
            "response_mime_type": response_mime_type,
        }
        self.model = genai.GenerativeModel(
            model_name=self.agent_model,
            generation_config=self.generation_config,
            system_instruction=self.agent_prompt,
            streaming=self.streaming,
            tools=self.tools,
        )

    async def invoke(self, query_role, query):

        chat_session = self.model.start_chat(history=[])
        chat_session.append_message(query_role, query)

        if self.streaming == False:
            response = chat_session.send_message(query)
            return response

        elif self.streaming == True:
            response_chunk = await chat_session.send_message(query)
            response += response_chunk

        chat_session.append_message(self.agent_name, response)
