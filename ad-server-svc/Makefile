# DATABASE_URL must be exported before running the migrate targets, e.g.
#   export DATABASE_URL="postgres://user:password@host:5432/postgres"
migrateup:
	migrate -path db/migration -database "$(DATABASE_URL)" -verbose up

migratedown:
	migrate -path db/migration -database "$(DATABASE_URL)" -verbose down

sqlc:
	sqlc generate

test:
	go test -v -race -cover ./...

server:
	go run main.go

mock:
	mockgen -package mockdb -destination db/mock/store.go adserver/db/sqlc Store

.PHONY: migrateup migratedown sqlc test server mock
