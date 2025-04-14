# See previous message for full content
Create a virtual env: python -m venv venv
Permission to access/enable venv on powershell: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
Command to active venv: .\venv\Scripts\Activate

# .env file sample

# OpenAI API Key
OPENAI_API_KEY=XXXXXXX

# Logging Configuration
LOG_MODE=both             # Options: terminal, file, both
LOG_FILE_PATH=logs/session.log

# end .env file sample

command to create empty init.py file
New-Item -Path .\test\__init__.py -ItemType File

# Dealer Desk Auto Voice Assistant

A virtual voice assistant for auto dealers, built using AutoGen 0.2.9 with multiple specialized agents.

## Features

- **Pricing Agent:** Calculates dealer incentives based on application details
- **Policy Agent:** Provides information about auto loan policies using RAG (Retrieval Augmented Generation)
- **Dealer Agent:** Handles dealer complaints and issues with a human-in-the-loop approach
- **Router Agent:** Directs user queries to the appropriate specialized agent

## Project Structure

```
voice_assistant_backend/
├── main.py                   # Entry point to launch GroupChatManager
├── agents/
│   ├── __init__.py
│   ├── router_agent.py       # Routes to PricingAgent / PolicyAgent / DealerAgent
│   ├── pricing_agent.py      # Handles dealer incentive calculation
│   ├── policy_agent.py       # Handles policy queries using RAG
│   ├── dealer_agent.py       # Logs dealer complaints with HiTL
├── rag/
│   ├── __init__.py
│   ├── loader.py             # Loads PDFs, splits, embeds using FAISS
│   ├── retriever.py          # Performs retrieval on embeddings
├── shared/
│   ├── __init__.py
│   ├── llm_config.py         # Central LLM config for all agents
│   ├── tools.py              # Common tools (API callers, utilities)
│   ├── schemas.py            # Pydantic models for agent input validation
├── test/
│   ├── test_agent_solution.py    # Test script for the complete agent system
│   ├── test_individual_agents.py # Test script for testing each agent separately
├── requirements.txt
└── README.md
```

## Setup and Installation

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Running the Application

To start the voice assistant:

```
python -m main
```

## Testing

### Testing the complete system:

```
python -m test.test_agent_solution
```

### Testing individual agents:

```
python -m test.test_individual_agents
```

## Agent Capabilities

### Router Agent
- Classifies user queries and directs them to the appropriate specialized agent
- Identifies incentive, policy, and complaint-related queries

### Pricing Agent
- Calculates dealer incentives using the formula: (contractAPR - buyRate) * 1000
- Collects all required parameters: dealerId, applicationNumber, contractAPR, buyRate

### Policy Agent
- Uses RAG to retrieve relevant information from policy documents
- Answers questions about auto loan policies, requirements, and eligibility
- First time running rag
- python
   >>> from rag.retriever import build_vectorstore
   >>> build_vectorstore()

### Dealer Agent
- Collects complaint details from dealers
- Logs formal complaints with application numbers and dealer IDs
- Can escalate issues to human specialists when needed

## Conversation Flow

1. User sends a query
2. Router Agent classifies the query
3. Specialized agent (Pricing/Policy/Dealer) processes the query
4. Specialized agent responds with a complete answer including [final_answer] tag
5. Conversation terminates or returns to user for more input


Here are some test queries you can try to test each of your agents:
For Pricing Agent:

"What would be the dealer incentive if I have an application APP5678 with contractAPR of 6.5% and buyRate of 3.8%?"
"How much incentive would I get as a dealer for application ABC123?"
"Calculate the dealer incentive for dealerId XYZ789, application DEF456, APR 7.2%, and buyRate 4.1%"

For Dealer Agent:

"I want to file a complaint about my incentive payment for application APP7890. I was promised $3000 but only received $2200."
"I'm having an issue with my dealer account. My application MNO456 was processed but I haven't received any payment yet."
"I need to escalate a concern about missing incentives for the last three applications I processed."

For Policy Agent:

"What are the documentation requirements for auto loans?"
"What's the policy on financing cars older than 10 years?"
"What are the eligibility criteria for getting an auto loan from Chase Bank?"
what is the policy for used car loans

##Testing Question set 2
Agent-Specific Questions
🔷 1. PolicyAgent (RAG-based)
Trigger RAG and document-grounded answers.

“What documents are required to apply for an auto loan?”

“Can I finance a 12-year-old vehicle?”

“What’s the policy on auto loans for used cars?”

“What are the eligibility criteria for Wells Fargo auto loans?”

“What is the interest rate for used car loans?”

➡️ These will invoke RAG, show chunk logs, and test fallback when info is missing.

🟩 2. PricingAgent (incentive calculator)
Make sure it asks for inputs and calculates correctly when provided.

“How much dealer incentive will I get for application ABC123?”

“Calculate dealer incentive for application APP5678 with contract APR 7.2% and buy rate 4.1%”

“What would be the incentive if contract APR is 6.5% and buy rate is 3.8%?”

➡️ Also test:

text
Copy
Edit
"I gave you the inputs earlier, please calculate now."
This will validate whether it can maintain context in a multi-turn flow.

🟥 3. DealerAgent (HiTL / complaint logger)
Tests issue-logging or escalation behavior.

“I need to report an issue with incentive payment for application XYZ123.”

“My dealer account is not showing the last three applications, can you help?”

“The incentive promised was $3000 but I received only $2200.”

➡️ Expect human-like acknowledgment and logging behavior.

🔄 RouterAgent Coverage
🧠 Validate routing based on intent detection:
“What’s the current balance of my auto loan?” → Should route to LoanBalanceAgent (if retained)

“I want to understand Wells Fargo’s used car financing policy.” → PolicyAgent

“Please calculate the incentive for APR 8% and buy rate 5%.” → PricingAgent

“I need to escalate an incentive issue.” → DealerAgent

➡️ Observe: that the message is rewritten with @TargetAgent: syntax and includes full user query.

🔁 Multi-Turn / Multi-Agent Scenarios
🌐 Scenario 1: Partial → Complete → Answer (PricingAgent)
text
Copy
Edit
User: What is the dealer incentive for application APP123?
Agent: Please share contract APR and buy rate.
User: APR is 7.5%, buy rate is 4.0%
Agent: The incentive is $3500. [final_answer]
🌐 Scenario 2: RAG fallback path (PolicyAgent)
text
Copy
Edit
User: Can I get loan for electric scooter?
Agent: No related document found. This answer is not based on retrieved documents.
🌐 Scenario 3: Policy → Pricing → Dealer escalation
text
Copy
Edit
User: What’s the eligibility for auto loan?
→ PolicyAgent answers from RAG

User: Okay, now calculate dealer incentive for application ID.
→ PricingAgent picks it up

User: That amount seems wrong, I want to file a complaint.
→ DealerAgent logs the complaint

# Changes done for 15th April demo - part1
- added shared context to preserve conversation context and user details.
- max_round count is set to 20 in groupchat.
- in llm config, added "cache_seed": None   
  - to disable the cache folder, need to manage in better way
- Added greetings before initiate chat to get user details and greet user.