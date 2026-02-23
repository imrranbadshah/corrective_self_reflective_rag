```

docker build -t imrranbadshah/crag-rag-app . ; docker tag imrranbadshah/crag-rag-app:latest 975050364113.dkr.ecr.ap-south-1.amazonaws.com/imrranbadshah/crag-rag-app:latest ; docker push 975050364113.dkr.ecr.ap-south-1.amazonaws.com/imrranbadshah/crag-rag-app:latest


aws ecr describe-images --repository-name imrranbadshah/crag-rag-app --region ap-south-1 --query 'imageDetails[*].imageTags'

eb init crag-rag-app-envf --platform "Docker running on 64bit Amazon Linux 2023" --region ap-south-1; eb create crag-rag-app-envf --instance-type t3.large --single; eb setenv OPENAI_API_KEY="test" TAVILY_API_KEY="test" QDRANT_URL="https://test.us-east-1-1.aws.cloud.qdrant.io:6333" QDRANT_API_KEY="test" RERANKER_BACKEND="local" UPLOAD_DIR="/var/app/uploads"

## Permissions
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

  3. Create the instance profile and attach the role:
  aws iam create-instance-profile --instance-profile-name aws-elasticbeanstalk-ec2-role

  aws iam add-role-to-instance-profile --instance-profile-name aws-elasticbeanstalk-ec2-role --role-name aws-elasticbeanstalk-ec2-role

  4. Also add ECR pull permission (since you're using ECR):
  aws iam attach-role-policy --role-name aws-elasticbeanstalk-ec2-role --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

```