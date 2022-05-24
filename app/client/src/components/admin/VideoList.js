import { Box, Grid, Modal, Paper, Typography } from '@mui/material'
import React from 'react'
import ReactPlayer from 'react-player'
import { getUrl } from '../../common/utils'
import SnackbarAlert from '../alert/SnackbarAlert'
import VideoListItem from './VideoListItem'

const URL = getUrl()

const EMPTY_STATE = (
  <Grid sx={{ height: '100%' }} container direction="row" justifyContent="center">
    <Grid container item justifyContent="center" sx={{ mt: 10 }}>
      <Typography
        variant="h4"
        sx={{
          fontFamily: 'monospace',
          fontWeight: 500,
          letterSpacing: '.2rem',
          color: 'inherit',
          textDecoration: 'none',
        }}
      >
        NO VIDEOS
      </Typography>
    </Grid>
  </Grid>
)

const VideoList = ({ videos }) => {
  const [alert, setAlert] = React.useState({ open: false })
  const [videoModal, setVideoModal] = React.useState({
    open: false,
  })

  const openVideo = (video) => {
    setVideoModal({
      open: true,
      id: video.video_id,
    })
  }

  const handleCopyPublicLink = () => {
    setAlert({
      type: 'info',
      message: 'Link copied to clipboard',
      open: true,
    })
  }

  return (
    <Box>
      <Modal open={videoModal.open} onClose={() => setVideoModal({ open: false })}>
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '95%',
            bgcolor: 'background.paper',
            // border: '2px solid #000',
            boxShadow: 24,
          }}
        >
          <ReactPlayer url={`${URL}/api/video?id=${videoModal.id}`} width="100%" height="auto" controls />
        </Box>
      </Modal>
      <SnackbarAlert severity={alert.type} open={alert.open} setOpen={(open) => setAlert({ ...alert, open })}>
        {alert.message}
      </SnackbarAlert>
      <Typography
        variant="h4"
        sx={{
          fontFamily: 'monospace',
          fontWeight: 500,
          letterSpacing: '.2rem',
          color: 'inherit',
          textDecoration: 'none',
          ml: 1,
        }}
      >
        MY VIDEOS...
      </Typography>
      <Paper variant="outlined" sx={{ minHeight: 200, maxHeight: 500, overflow: 'hidden' }}>
        {!videos && EMPTY_STATE}
        {videos && (
          <Grid container>
            {videos.map((v) => (
              <Grid key={v.video_id} item xs={12}>
                <VideoListItem video={v} openVideoHandler={openVideo} copyLinkHandler={handleCopyPublicLink} />
              </Grid>
            ))}
          </Grid>
        )}
      </Paper>
    </Box>
  )
}

export default VideoList
