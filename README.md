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
