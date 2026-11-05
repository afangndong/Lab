pipeline {
    agent any

    parameters {
        string(name: 'CHANGE_NO', defaultValue: 'CHG0030413', description: 'Ticketnummer')
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
                    . .venv/bin/activate
                    python scripts/gate.py "$CHANGE_NO"
                '''
            }
        }

        stage('Plan'){
            steps {
                sh '''
                    . .venv/bin/activate
                    ansible-playbook -i ansible/inventory.yml ansible/site.yml --check --diff
                '''
            }
        }

        stage('Freigabe'){
            steps {
                input message: "Plan geprüft? Rollout für ${params.CHANGE_NO} starten?", ok: 'Deploy'
            }
        }

        stage('Rollout'){
            steps {
                sh '''
                    . .venv/bin/activate
                    ansible-playbook -i ansible/inventory.yml ansible/site.yml
                '''
            }
        }
    }
}