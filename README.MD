# Ebay Kleinanzeigen API

<div align="center">
  <h3 align="center">Ebay Kleinanzeigen API</h3>

  <p align="center">
    A powerful API interface for Ebay-Kleinanzeigen.de that enables you to fetch listings and specific data.
  </p>

  <p align="center">
    <b>🚀 Looking for a ready-to-use solution?</b>
    <br />
    Try it at <a href="https://adspy.one"><strong>adspy.one »</strong></a>
    <br />
    ✓ Automated Search Agents
    <br />
    🔜 Hosted Scraper API (Coming Soon)
    <br />
    <a href="https://github.com/DanielWTE/ebay-kleinanzeigen-api/issues">Report Bug</a>
    ·
    <a href="https://github.com/DanielWTE/ebay-kleinanzeigen-api/issues">Request Feature</a>
  </p>
</div>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

### Want to skip the setup?
Visit [adspy.one](https://adspy.one) for our hosted solution with additional features and zero configuration required.

### Prerequisites
- Python 3.12 or higher
- pip (Python package manager)
- Playwright

### Installation

1. Clone the repository
```sh
git clone https://github.com/DanielWTE/ebay-kleinanzeigen-api.git
cd ebay-kleinanzeigen-api
```

2. Install dependencies
```sh
pip install -r requirements.txt
playwright install chromium
```

3. Start the API
```sh
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### API Endpoints

- `GET /inserate?page_count=5` - Fetch listings (default: 1 page, max: 20 pages)
- `GET /inserat/{id}` - Fetch details for a specific listing

### Documentation

#### API Response Format
All API endpoints return responses in the following JSON format:

API documentation is available at `http://localhost:8000/docs` when running locally.

## License
Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>
