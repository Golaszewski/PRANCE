To install the shaker module, follow the directions in the [pdf](https://github.com/Golaszewski/PRANCE/blob/main/perma_shaker/HT91108%20Shaker%20with%20USB%2C%20Manual.pdf) provided.

To run the shaker in a PyHamilton script, use

```python
from pyshaker.shaker import PyShaker
shaker = PyShaker(comport="COM14")
shaker.start(300)
shaker.stop()
```


![alt_text](https://github.com/Golaszewski/PRANCE/blob/main/perma_shaker/images/bigbear_image.png)
