import gradio as gr
import requests
import os  
import json
import transformers
from transformers import AutoTokenizer, AutoModelForCausalLM

hf_token = os.getenv("HF_AUTH_TOKEN")
vapi_url = "https://api-inference.huggingface.co/models/vectara/hallucination_evaluation_model"
headers = {"Authorization": f"Bearer {hf_token}"}


model_name = "allenai/OLMo-1B"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)

def generate_text(prompt, max_new_tokens=400, do_sample=True, top_k=50, top_p=0.95):
    inputs = tokenizer(prompt, return_tensors='pt', return_token_type_ids=False)
    response = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=do_sample, top_k=top_k, top_p=top_p)
    return tokenizer.batch_decode(response, skip_special_tokens=True)[0]


# Function to query the API
def query(payload):
    response = requests.post(vapi_url, headers=headers, json=payload)
    return response.json()

def check_hallucination(assertion, citation):
    api_url = "https://api-inference.huggingface.co/models/vectara/hallucination_evaluation_model"
    header = {"Authorization": f"Bearer {hf_token}"}
    payload = {"inputs": f"{assertion} [SEP] {citation}"}

    response = requests.post(api_url, headers=header, json=payload, timeout=120)
    output = response.json()
    output = output[0][0]["score"]

    return f"**hallucination score:** {output}"


def query_vectara(text):
    user_message = text
    customer_id = os.getenv('CUSTOMER_ID')
    corpus_id = os.getenv('CORPUS_ID')
    api_key = os.getenv('API_KEY')
    api_key_header = {
        "customer-id": customer_id,
        "x-api-key": api_key
    }
    request_body = {
        "query": [
            {
                "query": user_message,
                "queryContext": "",
                "start": 1,
                "numResults": 25,
                "contextConfig": {
                    "charsBefore": 0,
                    "charsAfter": 0,
                    "sentencesBefore": 2,
                    "sentencesAfter": 2,
                    "startTag": "%START_SNIPPET%",
                    "endTag": "%END_SNIPPET%",
                },
                "rerankingConfig": {
                    "rerankerId": 272725718,
                    "mmrConfig": {
                        "diversityBias": 0.35
                    }
                },
                "corpusKey": [
                    {
                        "customerId": customer_id,
                        "corpusId": corpus_id,
                        "semantics": 0,
                        "metadataFilter": "",
                        "lexicalInterpolationConfig": {
                            "lambda": 0
                        },
                        "dim": []
                    }
                ],
                "summary": [
                    {
                        "maxSummarizedResults": 5,
                        "responseLang": "auto",
                        "summarizerPromptName": "vectara-summary-ext-v1.2.0"
                    }
                ]
            }
        ]
    }
    response = requests.post(
        "https://api.vectara.io/v1/query",
        json=request_body,  
        verify=True,
        headers=api_key_header
    )

    if response.status_code == 200:
        query_data = response.json()
        if query_data:
            sources_info = []

            # Extract the summary.
            summary = query_data['responseSet'][0]['summary'][0]['text']

            # Iterate over all response sets
            for response_set in query_data.get('responseSet', []):
                # Extract sources
                # Limit to top 5 sources.
                for source in response_set.get('response', [])[:5]:
                    source_metadata = source.get('metadata', [])
                    source_info = {}

                    for metadata in source_metadata:
                        metadata_name = metadata.get('name', '')
                        metadata_value = metadata.get('value', '')

                        if metadata_name == 'title':
                            source_info['title'] = metadata_value
                        elif metadata_name == 'author':
                            source_info['author'] = metadata_value
                        elif metadata_name == 'pageNumber':
                            source_info['page number'] = metadata_value

                    if source_info:
                        sources_info.append(source_info)

            result = {"summary": summary, "sources": sources_info}
            return f"{json.dumps(result, indent=2)}"
        else:
            return "No data found in the response."
    else:
        return f"Error: {response.status_code}"

# Main function to integrate Vectara, OLMo, and hallucination check
def evaluate_content(user_input):
    vectara_summary = query_vectara(user_input)
    olmo_output = generate_text(vectara_summary)
    hallucination_score = check_hallucination(olmo_output, vectara_summary)    
    return olmo_output, hallucination_score

# Create the Gradio interface
iface = gr.Interface(
    fn=evaluate_content,
    inputs=[gr.Textbox(label="User Input")],
    outputs=[gr.Textbox(label="Generated Text"), gr.Textbox(label="Hallucination Score")],
    live=False,
    title="👋🏻Welcome to 🌟Team Tonic's 🧠🌈SureRAG🔴🟢",
    description="Nothing is more important than reputation. However you can create automated content pipelines for public facing content. How can businesses grow their reputation while mitigating risks due to AI? How it works : vectara rag retrieval reranking and summarization is used to return content. then an LLM generates content based on these returns. this content is checked for hallucination before being validated for publishing on twitter. SureRAG is fixed on Tonic-AI's README files as a Demo, provide input to generate a response. This response is checked by Vectara's HHME. Check out the model [vectara/hallucination_evaluation_model](https://huggingface.co/vectara/hallucination_evaluation_model) Join us : 🌟TeamTonic🌟 is always making cool demos! Join our active builder's🛠️community 👻  [![Join us on Discord](https://img.shields.io/discord/1109943800132010065?label=Discord&logo=discord&style=flat-square)](https://discord.gg/GWpVpekp) On 🤗Huggingface: [TeamTonic](https://huggingface.co/TeamTonic) & [MultiTransformer](https://huggingface.co/MultiTransformer) On 🌐Github: [Tonic-AI](https://github.com/tonic-ai) & contribute to 🌟 [DataTonic](https://github.com/Tonic-AI/DataTonic)",
)

# Launch the interface
iface.launch()