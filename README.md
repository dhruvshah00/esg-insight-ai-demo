# ESG Insights AI

**Simplifying ESG Materiality Analysis with AI for Asset Managers**

## Overview

ESG Insights AI is a platform designed to automate and streamline the analysis of Environmental, Social, and Governance (ESG) data for companies. Using advanced AI models such as Llama Index workflows and built with Next.js, the platform ensures that ESG evaluations comply with Global Reporting Initiative (GRI) standards. It helps asset managers efficiently analyze ESG risks, improve reporting accuracy, and make better-informed investment decisions while reducing manual effort.

### Key Features

- **AI-Driven Categorization**: Automates categorizing and prioritizing ESG data, allowing for faster assessments.
- **Automated Summaries**: Generates concise ESG summaries that comply with GRI standards, simplifying data interpretation.
- **Comprehensive Data Integration**: Collects data from various sources to provide a complete ESG profile.
- **GRI Compliance**: Ensures alignment with GRI standards for regulatory compliance.
- **Human-in-the-Loop Validation**: Allows human experts to review and validate AI-generated reports for enhanced accuracy.
- **Source Citation**: Each data point is linked back to its original source for full transparency.
- **Performance Monitoring**: Uses Arize Phoenix for real-time monitoring of AI model performance.
- **NVIDIA NIM for Scalability**: Ensures smooth operation during periods of high demand with NVIDIA NIM.

## Benefits

- **Time Efficiency**: Automation reduces the time spent on data gathering and reporting.
- **Improved Decision-Making**: Prioritizes material ESG risks, enhancing the quality of investment decisions.
- **Regulatory Compliance**: Ensures GRI-compliant ESG reports.
- **Stakeholder Transparency**: Provides detailed, transparent reports backed by source citations and expert validation.

## Future Enhancements

- **Expanded Data Sources**: Incorporate additional ESG data such as market sentiment and industry benchmarks.
- **Support for Multiple Standards**: Future updates will support standards like SASB and TCFD.
- **Customization**: Enable users to tailor analysis processes and thresholds for materiality.

## Project Structure

This project includes both backend and frontend services:

- **Backend**: FastAPI service for ESG data analysis.
- **Frontend**: Next.js service for the user interface.

### Environment Variables

For the backend service, you need to set the following environment variables in the `.env` file:

```bash
NVIDIA_API_KEY=
TAVILY_API_KEY=
PHOENIX_CLIENT_HEADERS=
PHOENIX_COLLECTOR_ENDPOINT=


## Getting Started

### Prerequisites
- Docker
- Docker Compose

### Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/your-username/esg-insights-ai.git
    cd esg-insights-ai
    ```

2. Set up the environment variables:

    - Create a `.env` file in the `backend` directory and add the required keys.

3. Build and run the Docker containers:

    ```bash
    docker-compose up --build
    ```

    The backend service will be available at `http://localhost:8000` and the frontend at `http://localhost:3000`.

## Contributing

We welcome contributions! Please read our [CONTRIBUTING.md](./CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for more details.

## Contact

For any questions or issues, feel free to open an issue on GitHub or reach out to the project maintainers.
