import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])


class Agent:
    def __init__(
        self,
        agent_name,
        agent_prompt,
        agent_model,
        temperature=1,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    ):
        self.agent_name = agent_name
        self.agent_prompt = agent_prompt
        self.agent_model = agent_model
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
        )

    def invoke(self, query_role, query):

        chat_session = self.model.start_chat(history=[])
        # append the user query to the chat session
        chat_session.append_message(query_role, query)

        # generate a response
        response = chat_session.send_message(query)
        # append the response to the chat session
        chat_session.append_message(self.agent_name, response)
