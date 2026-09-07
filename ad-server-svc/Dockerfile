# Build stage
FROM golang:1.21-alpine3.19 AS builder
WORKDIR /app
COPY . .
RUN go build -o main main.go
        
# Run stage
FROM alpine:3.19
WORKDIR /app
COPY --from=builder /app/main .
# No app.env is baked in: configuration comes from the environment at runtime.

EXPOSE 8080
CMD ["/app/main"]