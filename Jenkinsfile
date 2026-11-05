pipeline {
    agent any

    parameters {
        string(name: 'CHANGE_NO', defaultValue: 'CHG0030412', description: 'Ticketnummer')
    }

    environment {
        SERVICENOW_URL = 'http://host.docker.internal:8081'
    }

    stages {
        stage('Tests'){
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -q -r requirements.txt
                    pytest -q
                '''
            }
        }

        stage('Tor'){
            steps {
                sh '''
                    . . venv/bin/activate
                    python scripts/gate.py "$CHANGE_NO"
                '''
            }
        }
    }
}