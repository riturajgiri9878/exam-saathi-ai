# Plan B - Free Render Deployment

This configuration creates a free Render web service from a GitHub repository.

## Why lightweight mode is used

Render's free web-service tier has limited resources. The Plan B container does
not install the large sentence-transformer/PyTorch dependency. It automatically
uses Exam Saathi's tested TF-IDF recovery mode for topic ranking, note ranking,
and source retrieval.

The original Colab MVP and the main Cloud Run `Dockerfile` retain the embedding
architecture. Plan B is a safe demonstration deployment, not the final scaled
production environment.

## Deploy

1. Upload this folder to a GitHub repository.
2. Sign in to Render and connect the repository.
3. Choose **New > Blueprint** and select the repository containing `render.yaml`.
4. Review the proposed free web service and deploy it.
5. Watch the build logs until the service becomes live.

## Expected behavior

- The public URL remains the same across deploys.
- The free service can sleep after inactivity.
- The first request after sleep can take longer.
- Uploaded files are temporary and are not durable storage.
