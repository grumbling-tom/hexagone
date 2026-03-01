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

## deploy-backend: Build the Docker image, push to ECR, and update Lambda
.PHONY: deploy-backend
deploy-backend:
	$(eval ECR_URL := $(call tf_output,ecr_repository_url))
	$(eval IMAGE_TAG := $(shell git rev-parse --short HEAD))
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin "$(ECR_URL)"
	cd apps/backend && docker build -f Dockerfile.lambda --platform linux/arm64 -t hexagone-backend:latest .
	docker tag hexagone-backend:latest "$(ECR_URL):$(IMAGE_TAG)"
	docker push "$(ECR_URL):$(IMAGE_TAG)"
	aws lambda update-function-code \
		--function-name hexagone-backend \
		--image-uri "$(ECR_URL):$(IMAGE_TAG)" \
		--region $(AWS_REGION)
	@echo "Deployed backend image: $(ECR_URL):$(IMAGE_TAG)"

## deploy: Deploy both frontend and backend
.PHONY: deploy
deploy: deploy-frontend deploy-backend
