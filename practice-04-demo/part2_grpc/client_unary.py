import grpc

import order_pb2
import order_pb2_grpc


def main():
    channel = grpc.insecure_channel("localhost:50051")
    stub = order_pb2_grpc.OrderServiceStub(channel)

    created = stub.CreateOrder(order_pb2.CreateOrderRequest(product="Laptop", quantity=1))
    print("CreateOrder ->", created)

    fetched = stub.GetOrder(order_pb2.GetOrderRequest(order_id=created.order_id))
    print("GetOrder ->", fetched)


if __name__ == "__main__":
    main()
