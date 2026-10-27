import grpc

import order_pb2
import order_pb2_grpc


def main():
    channel = grpc.insecure_channel("localhost:50051")
    stub = order_pb2_grpc.OrderServiceStub(channel)

    created = stub.CreateOrder(order_pb2.CreateOrderRequest(product="Laptop", quantity=1))
    print("Created order", created.order_id, "- subscribing to updates...")

    for update in stub.StreamOrderUpdates(order_pb2.GetOrderRequest(order_id=created.order_id)):
        print("Update received:", update.new_status)


if __name__ == "__main__":
    main()
