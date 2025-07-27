# AgenticAIDay-Team_Northstar
## The problem
The Challenge: A bustling metropolis like Bengaluru generates millions of scattered data points every minute—from traffic updates and civic issues to spontaneous cultural events. This information is noisy, siloed across different platforms, and becomes outdated almost instantly. The challenge is not just to report news, but to find the signal in the noise and create a living pulse of the city.
The Objective: Build an agentic application that provides a live, synthesized, and intelligent view of the city. The agent should:
Fuse Disparate Data: Ingest real-time data from multiple sources (e.g., social media feeds, user-submitted reports). Instead of showing 15 separate posts about one traffic jam, the agent must use Gemini to synthesize them into a single, clean summary with actionable advice (e.g., "Heavy traffic on Old Airport Road, consider alternative routes.").
Enable Multimodal Citizen Reporting: Allow users to submit geo-tagged photos or videos of events (a fallen tree, a flash mob, a water-logged street). The agent will use Gemini's multimodal capabilities to analyze the media, categorize the event, describe the situation, and plot it on a map automatically.
Create a Predictive & Agentic Layer: Go beyond reporting. The agent should analyze event streams to provide predictive alerts (e.g., "Multiple power cut reports in HSR Layout suggest a potential grid issue."). It could also power intelligent notifications, allowing users to subscribe to clear, AI-generated summaries for their specific area or interests.
Visualize the Pulse: Present the synthesized information on a real-time, map-based dashboard built with a modern frontend and a scalable Firebase backend. (Bonus: Analyze public sentiment from posts to create a "mood map" for different events).
Tech Stack: Use of Google AI technologies is mandatory.
Special prize for using Firebase Studio and deploying the project



Frontend - React native
1. Install dependencies

   ```bash
   npm install
   ```

2. Start the app

   ```bash
   npx expo start
   ```


Swagger docs
- https://incident-reporter-66fji4lxba-uc.a.run.app/docs
- https://fastapi-event-api-66fji4lxba-uc.a.run.app/docs

Backend
   ```bash
   uvicorn Orchestrator:app --reload
   ```
![Architecture Diagram](https://github.com/kruthikakalmali/AgenticAIDay-Team_Northstar/blob/master/Architecture.png)
