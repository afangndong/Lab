pipeline {
    agent any

    parameters {
        string(name: 'CHANGE_NO', defaultValue: 'CHG0030412', description: 'Ticketnummer')
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
    }
}