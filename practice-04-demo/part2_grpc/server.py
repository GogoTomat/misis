import time
from concurrent import futures

import grpc

import order_pb2
import order_pb2_grpc

orders_db: dict[int, dict] = {}
next_id = 1


class OrderServiceServicer(order_pb2_grpc.OrderServiceServicer):
    def GetOrder(self, request, context):
        order = orders_db.get(request.order_id)
        if order is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "Order not found")
        return order_pb2.Order(
            order_id=order["id"],
            status=order["status"],
            product=order["product"],
            quantity=order["quantity"],
        )

    def CreateOrder(self, request, context):
        global next_id
        order_id = next_id
        next_id += 1
        orders_db[order_id] = {
            "id": order_id,
            "status": "DRAFT",
            "product": request.product,
            "quantity": request.quantity,
        }
        return order_pb2.Order(
            order_id=order_id,
            status="DRAFT",
            product=request.product,
            quantity=request.quantity,
        )

    def StreamOrderUpdates(self, request, context):
        statuses = ["CONFIRMED", "PACKED", "SHIPPED", "DELIVERED"]
        for status in statuses:
            time.sleep(1)
            order = orders_db.get(request.order_id)
            if order is not None:
                order["status"] = status
            yield order_pb2.OrderUpdate(order_id=request.order_id, new_status=status)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_pb2_grpc.add_OrderServiceServicer_to_server(OrderServiceServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server started on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
