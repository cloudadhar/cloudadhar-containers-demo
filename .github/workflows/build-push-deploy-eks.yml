name: Build, push to ECR, and deploy to ECS or EKS

on:
  push:
    branches:
      - test
      - main

  workflow_dispatch:
    inputs:
      target_environment:
        description: AWS account/environment to use
        required: true
        default: test
        type: choice
        options:
          - test
          - live

      deploy_to_ecs:
        description: Deploy the new image to ECS Fargate
        required: true
        default: false
        type: boolean

      deploy_to_eks:
        description: Deploy the new image to EKS
        required: true
        default: false
        type: boolean

permissions:
  contents: read
  id-token: write

env:
  AWS_REGION: ap-south-1
  ECR_REPOSITORY: cloudadhar-containers-demo
  K8S_NAMESPACE: cloudadhar
  K8S_DEPLOYMENT: cloudadhar-web

jobs:
  build-and-push:
    name: Build and push image
    runs-on: ubuntu-latest
    timeout-minutes: 20

    environment:
      name: ${{ github.event_name == 'workflow_dispatch' && inputs.target_environment || (github.ref_name == 'main' && 'live' || 'test') }}

    env:
      AWS_ROLE_ARN: ${{ vars.AWS_ROLE_ARN }}
      AWS_ACCOUNT_ID: ${{ vars.AWS_ACCOUNT_ID }}

    outputs:
      image_uri: ${{ steps.build.outputs.image_uri }}
      image_tag: ${{ steps.build.outputs.image_tag }}

    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Validate branch and environment mapping
        env:
          SELECTED_ENVIRONMENT: ${{ github.event_name == 'workflow_dispatch' && inputs.target_environment || (github.ref_name == 'main' && 'live' || 'test') }}
        run: |
          case "${GITHUB_REF_NAME}:${SELECTED_ENVIRONMENT}" in
            test:test|main:live)
              echo "Branch and environment mapping is valid."
              ;;
            *)
              echo "::error::Use branch test with environment test, or branch main with environment live."
              exit 1
              ;;
          esac

      - name: Validate AWS configuration
        run: |
          test -n "${AWS_ROLE_ARN}" || {
            echo "::error::AWS_ROLE_ARN is not configured in the selected GitHub environment."
            exit 1
          }

          test -n "${AWS_ACCOUNT_ID}" || {
            echo "::error::AWS_ACCOUNT_ID is not configured in the selected GitHub environment."
            exit 1
          }

      - name: Configure temporary AWS credentials through OIDC
        uses: aws-actions/configure-aws-credentials@v6.2.4
        with:
          role-to-assume: ${{ env.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
          allowed-account-ids: ${{ env.AWS_ACCOUNT_ID }}
          mask-aws-account-id: true

      - name: Verify AWS identity
        run: aws sts get-caller-identity

      - name: Sign in to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push commit and latest tags
        id: build
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          IMAGE_TAG="${GITHUB_SHA::12}"
          IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:${IMAGE_TAG}"
          LATEST_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:latest"

          docker build \
            --build-arg APP_VERSION="${IMAGE_TAG}" \
            --tag "${IMAGE_URI}" \
            --tag "${LATEST_URI}" \
            .

          docker push "${IMAGE_URI}"
          docker push "${LATEST_URI}"

          echo "image_uri=${IMAGE_URI}" >> "${GITHUB_OUTPUT}"
          echo "image_tag=${IMAGE_TAG}" >> "${GITHUB_OUTPUT}"
          echo "Published image: ${IMAGE_URI}"

  deploy-to-ecs:
    name: Deploy image to Amazon ECS
    needs: build-and-push
    if: ${{ (github.event_name == 'push' && github.ref_name == 'test') || (github.event_name == 'workflow_dispatch' && inputs.deploy_to_ecs == true) }}
    runs-on: ubuntu-latest
    timeout-minutes: 20

    environment:
      name: ${{ github.event_name == 'workflow_dispatch' && inputs.target_environment || 'test' }}

    env:
      AWS_ROLE_ARN: ${{ vars.AWS_ROLE_ARN }}
      AWS_ACCOUNT_ID: ${{ vars.AWS_ACCOUNT_ID }}
      ECS_CLUSTER_NAME: ${{ vars.ECS_CLUSTER_NAME }}
      ECS_SERVICE_NAME: ${{ vars.ECS_SERVICE_NAME }}
      ECS_TASK_DEFINITION: ${{ vars.ECS_TASK_DEFINITION }}
      ECS_CONTAINER_NAME: ${{ vars.ECS_CONTAINER_NAME }}

    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Validate ECS configuration
        run: |
          for VARIABLE_NAME in \
            AWS_ROLE_ARN \
            AWS_ACCOUNT_ID \
            ECS_CLUSTER_NAME \
            ECS_SERVICE_NAME \
            ECS_TASK_DEFINITION \
            ECS_CONTAINER_NAME
          do
            test -n "${!VARIABLE_NAME}" || {
              echo "::error::${VARIABLE_NAME} is not configured in the selected GitHub environment."
              exit 1
            }
          done

      - name: Configure temporary AWS credentials through OIDC
        uses: aws-actions/configure-aws-credentials@v6.2.4
        with:
          role-to-assume: ${{ env.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
          allowed-account-ids: ${{ env.AWS_ACCOUNT_ID }}
          mask-aws-account-id: true

      - name: Download current ECS task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition "${ECS_TASK_DEFINITION}" \
            --query taskDefinition \
            > task-definition.json

      - name: Insert new image into task definition
        id: render-ecs-task
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ env.ECS_CONTAINER_NAME }}
          image: ${{ needs.build-and-push.outputs.image_uri }}

      - name: Deploy new task definition to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.render-ecs-task.outputs.task-definition }}
          cluster: ${{ env.ECS_CLUSTER_NAME }}
          service: ${{ env.ECS_SERVICE_NAME }}
          wait-for-service-stability: true

      - name: Show ECS deployment
        run: |
          aws ecs describe-services \
            --cluster "${ECS_CLUSTER_NAME}" \
            --services "${ECS_SERVICE_NAME}" \
            --query 'services[0].deployments[*].{Status:status,TaskDefinition:taskDefinition,Running:runningCount,Desired:desiredCount}' \
            --output table

  deploy-to-eks:
    name: Deploy image to Amazon EKS
    needs: build-and-push
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.deploy_to_eks == true }}
    runs-on: ubuntu-latest
    timeout-minutes: 20

    environment:
      name: ${{ inputs.target_environment }}

    env:
      AWS_ROLE_ARN: ${{ vars.AWS_ROLE_ARN }}
      AWS_ACCOUNT_ID: ${{ vars.AWS_ACCOUNT_ID }}
      EKS_CLUSTER_NAME: ${{ vars.EKS_CLUSTER_NAME }}

    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Validate EKS configuration
        run: |
          for VARIABLE_NAME in AWS_ROLE_ARN AWS_ACCOUNT_ID EKS_CLUSTER_NAME
          do
            test -n "${!VARIABLE_NAME}" || {
              echo "::error::${VARIABLE_NAME} is not configured in the selected GitHub environment."
              exit 1
            }
          done

      - name: Configure temporary AWS credentials through OIDC
        uses: aws-actions/configure-aws-credentials@v6.2.4
        with:
          role-to-assume: ${{ env.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}
          allowed-account-ids: ${{ env.AWS_ACCOUNT_ID }}
          mask-aws-account-id: true

      - name: Configure kubectl
        run: |
          aws eks update-kubeconfig \
            --region "${AWS_REGION}" \
            --name "${EKS_CLUSTER_NAME}"

      - name: Apply Kubernetes resources
        env:
          IMAGE_URI: ${{ needs.build-and-push.outputs.image_uri }}
          IMAGE_TAG: ${{ needs.build-and-push.outputs.image_tag }}
        run: |
          sed \
            -e "s|IMAGE_URI_PLACEHOLDER|${IMAGE_URI}|g" \
            -e "s|APP_VERSION_PLACEHOLDER|${IMAGE_TAG}|g" \
            kubernetes/deployment.yaml | kubectl apply -f -

          kubectl apply -f kubernetes/service.yaml

          kubectl rollout status \
            deployment/"${K8S_DEPLOYMENT}" \
            --namespace "${K8S_NAMESPACE}" \
            --timeout 10m

          kubectl get deployments,pods,services \
            --namespace "${K8S_NAMESPACE}" \
            --output wide
