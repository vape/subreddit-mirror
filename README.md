### What is this?

Simple app to mirror the imgur images in a subreddit.
I'll only be mirroring the first 100 entries of the [/r/aww](http://www.reddit.com/r/aww) subreddit.

My girlfriend works at a company where access to reddit, imgur, and mirrors like filmot are banned.
I'm developing this app so that she can check out the top images from /r/aww.

I'm sure there are easier ways of achieving this goal. I just want to mess around with Python, Flask and Heroku so that's why I'm doing it this way.


### Project Structure

This app has one batch process which scrapes the first 100 entries on the /r/aww front page, gets all imgur image links, uploads them to an Amazon S3 bucket, and also saves all image urls.
The Flask app has only one page which retrieves the image urls from the database and runs them through a simple template to create the web page for the user.
