FROM public.ecr.aws/docker/library/python:3.12-alpine

LABEL org.opencontainers.image.title="CloudAdhar Containers Demo" \
      org.opencontainers.image.description="Sample container for Amazon ECR, ECS, EKS and AWS Fargate training"

WORKDIR /app

RUN addgroup -S cloudadhar && adduser -S cloudadhar -G cloudadhar

COPY app.py index.html ./

USER cloudadhar

ARG APP_VERSION=v1

ENV PORT=8080 \
    APP_VERSION=${APP_VERSION} \
    PLATFORM="Local container"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)" || exit 1

CMD ["python", "app.py"]
