import torch
from torch import nn


def device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class TemporalFusion(nn.Module):
    """Input B,V,T,D; temporal attention then masked mean/attention view fusion."""

    def __init__(self, features, classes, hidden=64, fusion="attention"):
        super().__init__()
        if fusion not in ("mean", "attention"):
            raise ValueError("Unknown fusion")
        self.fusion = fusion
        self.gru = nn.GRU(features, hidden, batch_first=True)
        self.time_attention = nn.Linear(hidden, 1)
        self.view_attention = nn.Linear(hidden, 1)
        self.head = nn.Linear(hidden, classes)

    def forward(self, x, mask):
        if x.ndim != 4 or mask.shape != x.shape[:2] or not mask.any(dim=1).all():
            raise ValueError("Expected B,V,T,D with at least one available view per incident")
        b, v, t, d = x.shape
        # Sanitizing masked views also avoids NaN propagation from missing data.
        x = x.masked_fill(~mask[:, :, None, None], 0)
        temporal, _ = self.gru(x.reshape(b * v, t, d))
        weights = self.time_attention(temporal).softmax(dim=1)
        views = (temporal * weights).sum(dim=1).reshape(b, v, -1)
        if self.fusion == "attention":
            scores = self.view_attention(views).squeeze(-1).masked_fill(~mask, float("-inf"))
            weights = scores.softmax(dim=1)
        else:
            weights = mask.float() / mask.sum(dim=1, keepdim=True)
        return self.head((views * weights[..., None]).sum(dim=1))
