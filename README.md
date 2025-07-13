# ReddWork - Reddit Job Posting Scraper & Analyzer

## Introduction

**ReddWork** is a software for collecting and analyzing IT job postings.  
It performs automated scraping from related subreddits, categorizes and indexes the extracted data to enable analysis of **keywords**, **technology trends**, and **required skills**.

Reddword is designed to monitor the evolution of in-demand skills in the IT sector, classifing job postings by role, enabling a better understanding of which types of jobs are most in demand.

---

## Key Features

- **Automated scraping**: Collects IT job postings from selected subreddits, extracting title, description and date.
- **Keyword extraction**: Uses NLP techniques to identify the most relevant technical terms (e.g., `Python`, `AWS`, `React`).
- **Role categorization**: Classifies job postings into IT roles (e.g., Backend, IA, Cloud).
- **Elasticsearch integration**: Indexes the collected data for fast querying and advanced filtering.
- **Interactive dashboards**: With Kibana, users can visualize trends, keyword frequency, number of posts per category and more.
- **Full containerization**: The entire system runs in Docker containers for easy deployment and portability.

---

## Project Architecture

The system is composed of multiple services:

### 1. Python App – Reddit Data Fetcher
- **Description**: Connects to Reddit using PRAW (Python Reddit API Wrapper) to fetch job-related posts.
- **Technology**: Python + PRAW
- **Motivation**: Provides structured, reliable data access using Reddit’s official API.

### 2. Fluentd – Data Ingestion Layer
- **Description**: Collects structured Reddit data and forwards it to Kafka.
- **Technology**: Fluentd
- **Port**: `24224`
- **Motivation**: Acts as a flexible log aggregator and pipeline input.

### 3. Kafka – Message Broker
- **Description**: Transports data between services in real time.
- **Technology**: Apache Kafka
- **Port**: `9092`
- **Motivation**: Ensures scalable and reliable message delivery.

### 4. Spark – Stream Processor
- **Description**: Processes incoming posts, applies ML models to extract skills and classify job categories.
- **Technology**: Apache Spark
- **Ports**:
  - `7077` – Spark master port  
  - `8080` – Spark Web UI
- **Motivation**: Supports real-time distributed processing of large data streams.

### 5. Elasticsearch – Data Indexing
- **Description**: Stores processed data and predictions for querying and visualization.
- **Technology**: Elasticsearch
- **Ports**:
  - `9200` – REST API  
  - `9300` – Internal cluster communication
- **Motivation**: Fast, scalable indexing and search engine for analytics.

### 6. Kibana – Data Visualization
- **Description**: Visual interface to explore and visualize job post data.
- **Technology**: Kibana
- **Port**: `5601`
- **Motivation**: Helps users analyze trends and extract insights from processed data.

---

## Why Docker?

Docker is used to manage all components of the RedDwork pipeline:

- **Isolation**: Each service runs in its own container
- **Portability**: Ensures consistent behavior across environments
- **Scalability**: Services can be scaled independently
- **Simple Orchestration**: All services launch together with Docker Compose

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)
- Reddit API credentials (see below)

### Reddit API Setup

1. Before starting the system, get your Reddit API credentials from [https://old.reddit.com/prefs/apps](https://old.reddit.com/prefs/apps) and put them inside the .env file :

    ```env
    REDDIT_CLIENT_ID=your_client_id
    REDDIT_CLIENT_SECRET=your_client_secret
    REDDIT_USER_AGENT=your_custom_user_agent
    ```

2. Clone the project repository and navigate to the project directory:

   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```
   
3. Start all services using Docker Compose with build flag:
   
   ```bash
   docker-compose up --build
   ```

5. Once the containers are running, you can access the following services:

   - **Kibana**: [http://localhost:5601](http://localhost:5601)
   - **Spark Web UI**: [http://localhost:8080](http://localhost:8080)
   - **Elasticsearch API**: [http://localhost:9200](http://localhost:9200)

---

## Data Analysis and Visualization

Open Kibana to explore interactive dashboards including:

  - Extracted job roles and skills

  - Classified job post categories (via machine learning)

  - Trend analysis over time

  - Keyword frequency analysis
