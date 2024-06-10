# 网络

## NAT

```mermaid
graph TD;
    A[Host Machine] -->|eth0| B[Router]
    A -->|virbr0| C[Virtual Network with NAT]
    C --> D[VM1]
    C --> E[VM2]
    D -->|NAT| B
    E -->|NAT| B

```

