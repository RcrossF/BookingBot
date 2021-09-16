rm my-deployment-package.zip
cd venv/lib/python3.8/site-packages
zip -r ../../../../my-deployment-package.zip .
cd ../../../../
zip -d my-deployment-package.zip pip
zip -g my-deployment-package.zip *.py
zip -g my-deployment-package.zip *.json
aws lambda update-function-code --function-name BookingBot --zip-file fileb://my-deployment-package.zip