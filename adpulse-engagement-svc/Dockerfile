# Build stage
FROM golang:1.25-alpine3.21 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o app

# Run stage: just the compiled binary, not the whole Go toolchain.
FROM alpine:3.21
WORKDIR /app
COPY --from=builder /app/app .
# No credentials are baked in: configuration comes from the environment at runtime.

# Run as a non-root user.
RUN addgroup -S app && adduser -S -G app -u 1000 app
USER app

ENV GIN_MODE=release
EXPOSE 8081
CMD ["./app"]
