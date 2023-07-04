coverage run --source=BackendProject,ImagesApp,SocialApp,UsersApp,SearchApp,MessageApp,utils --include=BackendProject/urls.py,utils/**/*.py,ImagesApp/**/*.py,SocialApp/**/*.py,UsersApp/**/*.py,SearchApp/**/*.py,MessageApp/**/*.py --omit=**/__pycache__/**,**/migrations/**,BackendProject/asgi.py,BackendProject/settings.py,BackendProject/wsgi.py manage.py test
ret=$?
coverage xml -o coverage-reports/coverage.xml
coverage report
exit $ret