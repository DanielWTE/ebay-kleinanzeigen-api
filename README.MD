# Ebay Kleinanzeigen API

[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

<div align="center">
  <h3 align="center">Ebay Kleinanzeigen API</h3>

  <p align="center">
    A powerful API interface for Ebay-Kleinanzeigen.de that enables you to fetch listings, specific data, and view information.
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

### Built With
* [![Python][Python]][Python-url]
* [![Docker][Docker]][Docker-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

### Want to skip the setup?
Visit [adspy.one](https://adspy.one) for our hosted solution with additional features and zero configuration required.

### Self-Hosting Instructions
First, clone the project to your desired location:
```sh
git clone https://github.com/DanielWTE/ebay-kleinanzeigen-api.git
```

### Prerequisites
Install Docker and Docker Compose on your machine:
[Get Docker](https://docs.docker.com/get-docker/)
(Note: This project is currently tested on Linux Ubuntu 22.04)

### Installation
1. Verify the folder is named "ebay-kleinanzeigen-api" (required for nginx.conf)
2. Add HTTP proxies to: ebay-kleinanzeigen-api/app/functions/getProxy.py (see comments)
3. Launch the service:
```sh
docker-compose up --build -d --scale app=3
```
This command starts 3 API replicas. Adjust the number as needed (max 20 due to NGINX config).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage
Send GET requests to interact with the API. For detailed documentation and examples, visit:
- [Professional Hosted Solution](https://adspy.one)
- [Self-Hosted Documentation](https://dwag.me/project/scraper)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## License
Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/DanielWTE/ebay-kleinanzeigen-api.svg?style=for-the-badge
[contributors-url]: https://github.com/DanielWTE/ebay-kleinanzeigen-api/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/DanielWTE/ebay-kleinanzeigen-api.svg?style=for-the-badge
[forks-url]: https://github.com/DanielWTE/ebay-kleinanzeigen-api/network/members
[stars-shield]: https://img.shields.io/github/stars/DanielWTE/ebay-kleinanzeigen-api.svg?style=for-the-badge
[stars-url]: https://github.com/DanielWTE/ebay-kleinanzeigen-api/stargazers
[issues-shield]: https://img.shields.io/github/issues/DanielWTE/ebay-kleinanzeigen-api.svg?style=for-the-badge
[issues-url]: https://github.com/DanielWTE/ebay-kleinanzeigen-api/issues
[license-shield]: https://img.shields.io/github/license/DanielWTE/ebay-kleinanzeigen-api.svg?style=for-the-badge
[license-url]: https://github.com/DanielWTE/ebay-kleinanzeigen-api/blob/main/LICENSE
[Python]: https://img.shields.io/badge/python-000000?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[Docker]: https://img.shields.io/badge/docker-000000?style=for-the-badge&logo=docker&logoColor=white
[Docker-url]: https://www.docker.com/