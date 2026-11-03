use pyo3::prelude::*;

#[pymodule]
mod rust_sha256 {
    use pyo3::prelude::*;
    use sha2::{Digest, Sha256};
    use std::fs::File;
    use std::io::Read;

    #[pyfunction]
    fn calculate_sha(file_path: String) -> PyResult<String> {
        let mut file = File::open(file_path)?;
        let mut hasher = Sha256::new();
        let mut buffer = [0u8; 64 * 1024];

        loop {
            let bytes_read = file.read(&mut buffer)?;

            if bytes_read == 0 {
                break;
            }

            hasher.update(&buffer[..bytes_read]);
        }

        let hash = hasher.finalize();

        Ok(hex::encode(hash))
    }
}
