# CloudAdhar Containers Demo

A small static web application used in the CloudAdhar **Containers on AWS** live class.

The same container image can be stored in Amazon ECR and deployed to:

- Amazon ECS on AWS Fargate
- Amazon ECS on EC2
- Amazon EKS managed node groups
- Amazon EKS with Fargate profiles

## Architecture

```text
GitHub source -> Docker build -> Amazon ECR -> ECS Fargate / Amazon EKS
```

## Files

- `Dockerfile` builds a small, non-root Python container image.
- `app.py` serves the application and the `/health` endpoint.
- `index.html` is the CloudAdhar demonstration page.
- `.dockerignore` excludes local development files.
- `kubernetes/deployment.yaml` deploys two Kubernetes pods.
- `kubernetes/service.yaml` exposes the pods inside the cluster.

## Prerequisites

- AWS Region: `ap-south-1`
- Existing ECR repository: `cloudadhar-containers-demo`
- Docker available locally or in AWS CloudShell
- AWS CLI credentials with permission to push to the repository

## 1. Clone the GitHub repository

```bash
git clone https://github.com/cloudadhar/cloudadhar-containers-demo.git
cd cloudadhar-containers-demo
```

## 2. Build the custom image

```bash
docker build -t cloudadhar-containers-demo:v1 .
docker images cloudadhar-containers-demo
```

## 3. Test the image before pushing

```bash
docker run --name cloudadhar-demo -d -p 8080:8080 \
  -e PLATFORM="Local Docker" \
  -e AWS_REGION="ap-south-1" \
  cloudadhar-containers-demo:v1
curl http://localhost:8080
docker stop cloudadhar-demo
docker rm cloudadhar-demo
```

Open `http://localhost:8080` before stopping the container if you are running Docker locally.

## 4. Authenticate Docker to Amazon ECR

```bash
AWS_REGION="ap-south-1"
AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_REPOSITORY="cloudadhar-containers-demo"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"
```

## 5. Tag and push the custom image

```bash
docker tag cloudadhar-containers-demo:v1 \
  "${ECR_REGISTRY}/${ECR_REPOSITORY}:v1"

docker push "${ECR_REGISTRY}/${ECR_REPOSITORY}:v1"
```

Verify the `v1` image under **Amazon ECR -> Repositories -> cloudadhar-containers-demo -> Images**.

## 6. Create a second version

Build a second image and tag it as `v2`:

```bash
docker build --build-arg APP_VERSION=v2 -t cloudadhar-containers-demo:v2 .
docker tag cloudadhar-containers-demo:v2 \
  "${ECR_REGISTRY}/${ECR_REPOSITORY}:v2"
docker push "${ECR_REGISTRY}/${ECR_REPOSITORY}:v2"
```

Use `v1` and `v2` during the ECS service update or Kubernetes rolling-update demonstration.

## 7. Use the image with Amazon EKS

Replace IMAGE_URI_PLACEHOLDER with the complete ECR image URI, including :v1, and replace APP_VERSION_PLACEHOLDER with v1.

```bash
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml
kubectl get deployments,pods,services -n cloudadhar
```

To demonstrate a rolling update:

```bash
kubectl set image deployment/cloudadhar-web \
  web="${ECR_REGISTRY}/${ECR_REPOSITORY}:v2" \
  -n cloudadhar

kubectl rollout status deployment/cloudadhar-web -n cloudadhar
```

## GitHub Actions: build, push and optionally deploy

The workflow at .github/workflows/build-push-deploy-eks.yml uses GitHub OIDC to obtain short-lived AWS credentials. Do not create an IAM user or save AWS access keys in GitHub.

### GitHub environments

Under **Repository -> Settings -> Environments**, create:

- test
- live

Create these environment variables in both environments:

| Variable | Example |
| --- | --- |
| AWS_ACCOUNT_ID | AWS account ID for that environment |
| AWS_ROLE_ARN | arn:aws:iam::ACCOUNT_ID:role/cloudadhar-github-actions-eks-role |
| EKS_CLUSTER_NAME | EKS cluster name in that account |

Add an approval rule to the live environment before using this workflow for a production-style demonstration.

### AWS OIDC configuration

Repeat this setup in each AWS account:

1. Open **IAM -> Identity providers -> Add provider**.
2. Select **OpenID Connect**.
3. Provider URL: https://token.actions.githubusercontent.com
4. Audience: sts.amazonaws.com
5. Create role cloudadhar-github-actions-eks-role.
6. Replace AWS_ACCOUNT_ID_PLACEHOLDER in iam/github-actions-trust-policy.json and use it as the role trust policy.
7. Replace the account and cluster placeholders in iam/github-actions-permissions-policy.json and attach it as an inline permissions policy.

The trust policy restricts GitHub's OIDC subject to this repository's `test` and `live` environments. If the repository is renamed or transferred, update the repository name in the trust policy subjects.

### Authorize the role inside EKS

AWS IAM permission to call eks:DescribeCluster and Kubernetes authorization are separate controls. Create an EKS access entry for the GitHub Actions role before enabling deployment:

1. Open **EKS -> cluster -> Access -> Create access entry**.
2. IAM principal: the cloudadhar-github-actions-eks-role ARN.
3. Type: **Standard**.
4. Associate an appropriate EKS access policy.

For a short lab, cluster administrator access is convenient. In production, restrict deployment access to the cloudadhar namespace and apply least privilege.

### Workflow behavior

- A push to test builds and pushes the image to the **test** account.
- A push to main builds and pushes the image to the **live** account.
- **Actions -> Build, push to ECR, and deploy to EKS -> Run workflow** lets you choose test or live.
- Leave **Deploy the new image to EKS** disabled until the EKS cluster and access entry exist.
- Enable it to update the Kubernetes Deployment and wait for a successful rollout.
- Each build receives a traceable tag based on the Git commit SHA, and also updates the demonstration latest tag.

For production, pin third-party GitHub Actions to reviewed commit SHAs and use separate build and promotion workflows instead of rebuilding independently for each environment.

## Important teaching point

GitHub stores the application source and Dockerfile. Amazon ECR stores the built container image. ECS and EKS pull that image from ECR and run it.
