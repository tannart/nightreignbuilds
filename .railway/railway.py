from railway_sdk import define_railway, project, service

# This repository manages only its own resources in the environment. Other
# repositories export their own partial name.
# See https://docs.railway.com/infrastructure-as-code#multi-repo-projects
PARTIAL = "web"


@define_railway
def main(ctx=None):
    web = service(
        "web",
        start=(
            "python manage.py collectstatic --noinput"
            " && gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2"
        ),
        healthcheck="/",
        preDeploy=(
            "python manage.py migrate --noinput && python manage.py seed_game_data"
        ),
        replicas={"ams": 1},
    )
    return project("nightreign-build", variables={"managed": False}, resources=[web])
