migrateup: 
	migrate -path db/migration -database "postgres://postgres.htppxkcokqiphaqkpnjc:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:5432/postgres" -verbose up

migratedown: 
	migrate -path db/migration -database "postgres://postgres.htppxkcokqiphaqkpnjc:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:5432/postgres" -verbose down

sqlc:
	sqlc generate

test:
	go test -v -race -cover ./... 

server:
	go run main.go

mock:
	mockgen -package mockdb -destination db/mock/store.go adserver/db/sqlc Store

.PHONY:	postgres createdb dropdb migrateup migratedown sqlc server mock 