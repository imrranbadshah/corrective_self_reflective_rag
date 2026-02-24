To configure Beanstalk we need to install a tool:
[Beanstalk AWS Link](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3.html)

If python exists in system.
```bash
# if python is installed, then set up the env variables for account and not system env variables.
python pip install awsebcli --upgrade --user
```


## Docker Commands to build the image
```bash
docker build -t imrranbadshah/crag-rag-app . ; 

docker tag imrranbadshah/crag-rag-app:latest 975050364113.dkr.ecr.ap-south-1.amazonaws.com/imrranbadshah/crag-rag-repo:latest ; 

docker push 975050364113.dkr.ecr.ap-south-1.amazonaws.com/imrranbadshah/crag-rag-repo:latest

```

## To check the ECR repository name in aws:
```bash
aws ecr describe-images --repository-name imrranbadshah/crag-rag-repo --region ap-south-1 --query 'imageDetails[*].imageTags'
```

| Level|Command|Name Example|Purpose |
|------|------|------|------|
| Application|eb init|crag-rag-app|The high-level project name. |
| Environment|eb create|crag-rag-prod|"The specific `running instance` for Production." |


## Application Creations command in Beanstalk
```bash
eb init crag-rag-prod --platform "Docker running on 64bit Amazon Linux 2023" --region ap-south-1; # manual

eb init crag-rag-prod --platform docker --region ap-south-1;   # Docker/GitActions
```

## Environment  Creations command in Beanstalk
```bash
eb create crag-rag-app --instance-type t3.medium --single; 
```

## Setting Env variables in BeanStalk
```bash
eb setenv OPENAI_API_KEY="test" TAVILY_API_KEY="test" QDRANT_URL="https://test.us-east-1-1.aws.cloud.qdrant.io:6333" QDRANT_API_KEY="test" RERANKER_BACKEND="local" UPLOAD_DIR="/var/app/uploads"
```

## Permissions needed for the BeanStalk to access the ECR
```bash
aws iam create-role --role-name aws-elasticbeanstalk-ec2-role --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}'

aws iam attach-role-policy --role-name aws-elasticbeanstalk-ec2-role --policy-arn arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier

aws iam attach-role-policy --role-name aws-elasticbeanstalk-ec2-role --policy-arn arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier

aws iam attach-role-policy --role-name aws-elasticbeanstalk-ec2-role --policy-arn arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker
```

## Role creations in IAM.
 ```bash
# Create the instance profile and attach the role:
aws iam create-instance-profile --instance-profile-name aws-elasticbeanstalk-ec2-role

aws iam add-role-to-instance-profile --instance-profile-name aws-elasticbeanstalk-ec2-role --role-name aws-elasticbeanstalk-ec2-role

# Also add ECR pull permission (since you're using ECR):
aws iam attach-role-policy --role-name aws-elasticbeanstalk-ec2-role --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

```

## To terminate all the Beanstalk related deployed applications
```bash
eb terminate -all --force
```