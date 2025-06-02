import os
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
load_dotenv()


def get_structured_data(transcript: str) -> int:
    # Load OpenAI API key from environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Set up the LLM with the OpenAI model
    llm = OpenAI(openai_api_key=openai_api_key,
                 temperature=0, model_name="gpt-4o")

    # Define the prompt template
    prompt_template = """
    You are a helpful assistant that classifies call transcripts into one of the following categories:You are an AI assistant that receives a transcript of a customer phone call between an AI voice agent and a user.
    Your task is to analyze the transcript and determine if the customer:


    1. Qualification: If the customer is still interested in the offer. Possible answers: Y(yes), N(no), ?(not clear)
    2. Upsell: If the customer is open to the upsell offer that was proposed. Possible answers: Y(yes), N(no), ?(not clear)
    3. Interested in podcast: if the customer is interested in the podcast: Possible answers: Y(yes), N(no), ?(not clear)
    4. Linkedin. Possible answers: Y(yes), N(no), ?(not clear)
    5. NPS score: Value from 0 to 10, how much the customer would recomend the service 
    6. Why: summary based on why it would recommend it 
    7. Upsell value: the value they say for the upsell

    Return the result in JSON format like this:
    {
    "qualification": "Y",
    "upsell": "Y",
    "upsellValue": 200,
    "interestedInPodcast": "N",
    "linkedin": "N",
    "nps": 7,
    "why": "because he did not liked the UI that much"
    }

    Don't include ```json or anything else, just the JSON object.

    Transcript:
    {transcript}

    """


    # Set up the LangChain prompt template and chain
    prompt = PromptTemplate(template=prompt_template,
                            input_variables=["transcript"])
    chain = LLMChain(llm=llm, prompt=prompt)

    # Run the chain and get the result
    response = chain.run(transcript)

    # Parse and return the result as an integer
    return response

