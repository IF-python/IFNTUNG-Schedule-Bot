## IFNTUNG-Schedule-Bot
![Create app](https://pbs.twimg.com/profile_images/514049439506255872/Df3buLtw_400x400.png)

## Deploy to Heroku
* `git clone https://github.com/P-Alban/IFNTUNG-Schedule-Bot`
* `cd IFNTUNG-Schedule-Bot`
* `heroku login`
* `heroku create <app-name> --region eu`
* `heroku git:remote -a <app-name>`
* `heroku addons:create heroku-postgresql:hobby-dev`
* `heroku addons:create heroku-redis:hobby-dev`
* `heroku config:set BOT_TOKEN=<bot-token>`
* `git push heroku master`
* `heroku ps:scale web=1`
* `heroku ps:scale worker=1`
* `heroku logs --tail`
