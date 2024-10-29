<a name="readme-top"></a>

[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]


<br />
<div align="center">

<h3 align="center">Ebay Kleinanzeigen API</h3>

  <p align="center">
    This tool acts as an API interface, you can use it to get random listings from Ebay-Kleinanzeigen.de, exact data from specific listings and even views of listings. 
    <br />
    <a href="https://dwag.me/project/scraper"><strong>Explore the docs »</strong></a>
    <br/>
    <a href="https://adspy.one"><strong>Search agents and hosted scraper API »</strong></a>
    <br />
    <br />
    ·
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

First of all, you need to clone the project.
Go to your folder where you want to clone the project and run the following command:

```sh
git clone https://github.com/DanielWTE/ebay-kleinanzeigen-api.git
```

### Prerequisites

Now, install Docker and Docker Compose on your machine. You can find the installation instructions for your operating system here:
[Get Docker](https://docs.docker.com/get-docker/)

(This project (for now) is not tested on Windows, only on Linux Ubuntu 22.04)

### Installation

1. Check if the folder is named "ebay-kleinanzeigen-api", if not you need to change the nginx.conf file in the nginx folder.
2. Add HTTP proxies to this file: ebay-kleinanzeigen-api/app/functions/getProxy.py (you will find a comment there)
3. You're ready to go, just run the following command in the root folder of the project:

```sh
docker-compose up --build -d --scale app=3
```

With this command, you start 3 replicas of the API. You can change the number of replicas to your liking. (max 20 due to NGINX config)

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Usage

Simple: Just send a GET request to the API.

You can use the API in your own projects or just use it to get random listings from Ebay-Kleinanzeigen.de. You can find the documentation or examples here: [Documentation](https://dwag.me/project/scraper)

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