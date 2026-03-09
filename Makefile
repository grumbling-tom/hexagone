TERRAFORM_DIR := terraform/production
AWS_REGION := eu-west-1

# Terraform output helpers
tf_output = $(shell terraform -chdir=$(TERRAFORM_DIR) output -raw $(1))

## deploy-frontend: Build the frontend and deploy to S3 + CloudFront
.PHONY: deploy-frontend
deploy-frontend:
	pnpm -C apps/web build
	aws s3 sync apps/web/dist/ s3://$(call tf_output,s3_bucket_name) --delete
	aws cloudfront create-invalidation \
		--distribution-id $(call tf_output,cloudfront_distribution_id) \
		--paths "/*"

## build-backend: Build the backend Docker image and push to ECR
.PHONY: build-backend
build-backend:
	$(eval ECR_URL := $(call tf_output,ecr_repository_url))
	$(eval IMAGE_TAG := $(shell git rev-parse --short HEAD))
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin "$(ECR_URL)"
	cd apps/backend && docker build -f Dockerfile.lambda --platform linux/arm64 -t hexagone-backend:latest .
	docker tag hexagone-backend:latest "$(ECR_URL):$(IMAGE_TAG)"
	docker push "$(ECR_URL):$(IMAGE_TAG)"
	@echo "Pushed backend image: $(ECR_URL):$(IMAGE_TAG)"

## deploy-backend: Build the Docker image, push to ECR, and update Lambda
.PHONY: deploy-backend
deploy-backend: build-backend
	$(eval ECR_URL := $(call tf_output,ecr_repository_url))
	$(eval IMAGE_TAG := $(shell git rev-parse --short HEAD))
	aws lambda update-function-code \
		--function-name hexagone-backend \
		--image-uri "$(ECR_URL):$(IMAGE_TAG)" \
		--region $(AWS_REGION)
	aws lambda update-function-code \
		--function-name hexagone-db-ops \
		--image-uri "$(ECR_URL):$(IMAGE_TAG)" \
		--region $(AWS_REGION)
	aws lambda update-function-code \
		--function-name hexagone-upload-processor \
		--image-uri "$(ECR_URL):$(IMAGE_TAG)" \
		--region $(AWS_REGION)
	@echo "Deployed backend image: $(ECR_URL):$(IMAGE_TAG)"

## deploy-db-migrate: Run database migrations via the db-ops Lambda
.PHONY: deploy-db-migrate
deploy-db-migrate:
	aws lambda invoke \
		--function-name hexagone-db-ops \
		--payload $$(echo '{"action":"migrate"}' | base64) \
		--region $(AWS_REGION) \
		/dev/stdout

## wait: Wait for the db-ops Lambda to be updated before running migrations
.PHONY: wait
wait:
	@echo "Waiting for db-ops lambda function code update..."
	@sleep 5

## deploy: Deploy both frontend and backend
.PHONY: deploy
deploy: deploy-frontend deploy-backend wait deploy-db-migrate
