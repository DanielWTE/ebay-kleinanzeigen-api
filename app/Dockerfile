# Using a python small basic image
FROM python:3.9

# Adding trusting keys to apt for repositories
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -

# Adding Google Chrome to the repositories
RUN wget -nc https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
# Updating apt to see and install Google Chrome
RUN apt-get -y update
# Installing Google Chrome
RUN apt-get -y install -f ./google-chrome-stable_current_amd64.deb
# Download Chrome Driver for installed Google Chrome version
RUN wget -N "https://storage.googleapis.com/chrome-for-testing-public/$(google-chrome --version | awk '{print $3}')/linux64/chromedriver-linux64.zip" && \
    unzip chromedriver-linux64.zip -d /usr/local/bin/ && \
    rm chromedriver-linux64.zip && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    rm -r /usr/local/bin/chromedriver-linux64 && \
    chmod +x /usr/local/bin/chromedriver

# Exposing our app port in docker internal network
EXPOSE 80

# Creates a dir for our application
WORKDIR /app

# copy our requirements.txt file and install dependencies
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy the rest of our application
COPY . .

# run the application
CMD python server.py